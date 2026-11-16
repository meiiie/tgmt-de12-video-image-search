#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use rand::RngCore;
use serde::{Deserialize, Serialize};
#[cfg(windows)]
use std::os::windows::io::AsRawHandle;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
use std::{
    fs,
    io::{BufRead, BufReader},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
use tauri::Manager;

#[derive(Clone, Serialize)]
struct Connection {
    port: u16,
    token: String,
}
#[derive(Default)]
struct Worker {
    child: Option<Child>,
    connection: Option<Connection>,
    error: Option<String>,
    job: Option<usize>,
}
type SharedWorker = Arc<Mutex<Worker>>;

fn hidden(command: &mut Command) -> &mut Command {
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    command
}

fn launch(app: &tauri::App, shared: SharedWorker) -> Result<(), Box<dyn std::error::Error>> {
    let data = app.path().app_data_dir()?;
    fs::create_dir_all(&data)?;
    let resource = app.path().resource_dir()?;
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let (python, engine) = if cfg!(debug_assertions) {
        (repo.join("desktop/runtime314/python.exe"), repo)
    } else {
        (resource.join("runtime/python.exe"), resource.join("engine"))
    };
    if !python.is_file() {
        return Err(format!("Không tìm thấy runtime: {}", python.display()).into());
    }
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    let token: String = bytes.iter().map(|byte| format!("{byte:02x}")).collect();
    let log = data.join("worker.log");
    if log.is_file() {
        let _ = fs::copy(&log, data.join("worker.previous.log"));
    }
    let mut command = Command::new(python);
    hidden(&mut command).args(["-u", "-c", "import sys, runpy; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('desktop.backend.server', run_name='__main__')"])
        .arg(&engine).arg("--data-dir")
        .arg(&data).arg("--parent").arg(std::process::id().to_string())
        .current_dir(engine).env("FRAMEATLAS_TOKEN", &token)
        .env("HF_HUB_DISABLE_TELEMETRY", "1").env("DO_NOT_TRACK", "1")
        .env("TOKENIZERS_PARALLELISM", "false")
        .stdin(Stdio::null()).stdout(Stdio::piped()).stderr(fs::File::create(log)?);
    let mut child = command.spawn()?;
    #[cfg(windows)]
    unsafe {
        use windows_sys::Win32::Foundation::CloseHandle;
        use windows_sys::Win32::System::JobObjects::*;
        let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if !job.is_null() {
            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let configured = SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &limits as *const _ as _,
                std::mem::size_of_val(&limits) as u32,
            );
            if configured != 0 && AssignProcessToJobObject(job, child.as_raw_handle()) != 0 {
                shared.lock().map_err(|e| e.to_string())?.job = Some(job as usize);
            } else {
                CloseHandle(job);
            }
        }
    }
    let stdout = child.stdout.take().ok_or("Worker output unavailable")?;
    shared.lock().map_err(|e| e.to_string())?.child = Some(child);
    thread::spawn(move || {
        #[derive(Deserialize)]
        struct Ready {
            port: u16,
        }
        for line in BufReader::new(stdout).lines() {
            match line {
                Ok(line) => {
                    if let Ok(ready) = serde_json::from_str::<Ready>(&line) {
                        if let Ok(mut worker) = shared.lock() {
                            worker.connection = Some(Connection {
                                port: ready.port,
                                token: token.clone(),
                            });
                        }
                    }
                }
                Err(_) => break,
            }
        }
        if let Ok(mut worker) = shared.lock() {
            worker.connection = None;
            worker.error = Some(
                "Bộ xử lý đã dừng. Xem worker.log trong thư mục dữ liệu hoặc mở lại ứng dụng."
                    .into(),
            );
        }
    });
    Ok(())
}

#[tauri::command]
async fn connection(worker: tauri::State<'_, SharedWorker>) -> Result<Connection, String> {
    let shared = worker.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let started = Instant::now();
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .map_err(|e| e.to_string())?;
        while started.elapsed() < Duration::from_secs(60) {
            let connection = {
                let worker = shared.lock().map_err(|e| e.to_string())?;
                if let Some(error) = &worker.error {
                    return Err(error.clone());
                }
                worker.connection.clone()
            };
            if let Some(connection) = connection {
                if client
                    .get(format!("http://127.0.0.1:{}/health", connection.port))
                    .bearer_auth(&connection.token)
                    .send()
                    .is_ok_and(|r| r.status().is_success())
                {
                    return Ok(connection);
                }
            }
            thread::sleep(Duration::from_millis(150));
        }
        Err("Bộ xử lý chưa sẵn sàng sau 60 giây. Kiểm tra worker.log hoặc thử lại.".into())
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn reveal(video_id: String, worker: tauri::State<'_, SharedWorker>) -> Result<(), String> {
    if !video_id.chars().all(|c| c.is_ascii_hexdigit()) || video_id.len() != 24 {
        return Err("Invalid video ID".into());
    }
    let connection = worker
        .lock()
        .map_err(|e| e.to_string())?
        .connection
        .clone()
        .ok_or("Worker unavailable")?;
    tauri::async_runtime::spawn_blocking(move || {
        #[derive(Deserialize)]
        struct Source {
            path: String,
        }
        let source: Source = reqwest::blocking::Client::new()
            .get(format!(
                "http://127.0.0.1:{}/videos/{}",
                connection.port, video_id
            ))
            .bearer_auth(connection.token)
            .timeout(Duration::from_secs(10))
            .send()
            .and_then(|r| r.error_for_status())
            .map_err(|e| e.to_string())?
            .json()
            .map_err(|e| e.to_string())?;
        let path = PathBuf::from(source.path);
        if !path.is_file() {
            return Err("File nguồn không còn ở vị trí đã nhập".into());
        }
        hidden(Command::new("explorer.exe").arg(format!("/select,{}", path.display())))
            .spawn()
            .map_err(|e| e.to_string())?;
        Ok(())
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
fn open_model_page() -> Result<(), String> {
    hidden(Command::new("explorer.exe").arg("https://huggingface.co/google/embeddinggemma-2"))
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}

fn main() {
    let shared: SharedWorker = Arc::new(Mutex::new(Worker::default()));
    let setup_worker = shared.clone();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_dialog::init())
        .manage(shared.clone())
        .invoke_handler(tauri::generate_handler![
            connection,
            reveal,
            open_model_page
        ])
        .setup(move |app| {
            if let Err(error) = launch(app, setup_worker.clone()) {
                if let Ok(mut worker) = setup_worker.lock() {
                    worker.error = Some(error.to_string());
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("FrameAtlas could not initialize");
    app.run(move |_, event| {
        if let tauri::RunEvent::Exit = event {
            if let Ok(mut worker) = shared.lock() {
                if let Some(child) = worker.child.as_mut() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
                #[cfg(windows)]
                if let Some(job) = worker.job.take() {
                    unsafe {
                        windows_sys::Win32::Foundation::CloseHandle(job as _);
                    }
                }
            }
        }
    });
}
