# FrameAtlas for Windows

FrameAtlas finds moments in local video files using text or an image. It opens the source at the matching time, saves named intervals and exports accurate, re-encoded MP4 clips. Original videos are never moved or deleted.

## First launch

1. Launch the Windows build. The native shell starts and owns its local worker automatically.
2. Open **Cài đặt** to select an existing EmbeddingGemma 2 directory, or leave the path empty to download the official pinned weights. The first download needs roughly 1.5 GB plus tokenizer files. Loading text and vision uses additional memory; 16 GB RAM is recommended for this CPU build.
3. Choose **Thêm video** or **Thêm thư mục**. Dragging files/folders into the native window also imports them. Folder imports include supported videos in subfolders.
4. Search while completed batches become available. Use Vietnamese or English, or upload a PNG/JPEG/WebP query. `Ctrl+K` returns to text entry; `Escape` closes the inspector.
5. Select a result, play the video, adjust start/end in seconds, and save or export the interval. Export requires a new `.mp4` filename and never overwrites an existing file.

**Hoạt động** exposes progress, pause, resume, cancel and retry. Pause takes effect at the next inference-batch boundary. **Quét thay đổi** checks imported folders and known files for additions/changes; it is an explicit scan, not an operating-system watcher. Removing a library entry removes its saved moments/index only. A later scan of its tracked folder can discover that source again; stop tracking the folder to prevent that.

**Lần xuất hiện** is available when a single video is selected. It identifies candidate events from similarity peaks, not a guaranteed count of real-world actions. No nth candidate means no result.

## Data and offline use

The per-user data directory is shown in Settings (normally `%APPDATA%\app.frameatlas.desktop`). It contains `library.sqlite3`, thumbnails, compatible preview copies, downloaded models, `worker.log` and one previous log. Copy the whole directory with the app closed to back it up. Keep original videos at their recorded paths. The app does not upload videos, queries or usage analytics. The first model download contacts Hugging Face; subsequent automatic loads use the completed local model.

MP4/H.264 sources play directly. Other formats are converted to an H.264/AAC preview on first open; long sources can take time. Export re-encodes the selected interval with FFmpeg for precise boundaries. The app needs WebView2, which the installer can provision if missing.

## Development on Windows

Prerequisites: Node.js, Rust stable with MSVC build tools, and any Python 3.10+ environment with pip available to run the bootstrap script. The packaged engine runs isolated Python **3.14.10**, independently of system Python.

```powershell
# From the repository root, using the existing development environment:
.venv\Scripts\python.exe scripts\bootstrap_desktop_runtime.py
cd desktop
npm ci
npm run tauri -- dev
```

The bootstrap verifies the official Python/FFmpeg archive hashes and installs the exact versions in `runtime-requirements.lock` into ignored `desktop/runtime314/`. The runtime is intentionally CPU-portable. CUDA requires a separately validated CUDA-enabled PyTorch distribution; automatic device selection alone cannot add CUDA to this CPU package.

```powershell
# Type checking and production frontend:
npm run build
# UI behavior against real HTTP/media services and deterministic embedding fixtures:
npm run test:ui
# Windows installer (includes runtime and FFmpeg, excludes model weights):
npm run tauri -- build
```

Installer output: `desktop/src-tauri/target/release/bundle/nsis/`. The build is unsigned unless a signing identity is supplied by the distributor. The unbundled executable needs the adjacent `runtime` and `engine` resource folders.

Backend checks from repository root:

```powershell
.venv\Scripts\python.exe -m pytest desktop/tests -q
.venv\Scripts\python.exe scripts/audit_temporal.py
desktop\runtime314\python.exe scripts/probe_eg2_desktop.py
desktop\runtime314\python.exe scripts/accept_desktop_real.py
```

The last two probes require the local acceptance models/media documented in `docs/desktop-verification.md`. They are separate from fixture tests. See `THIRD_PARTY.md` for dependency and sample provenance.

## Codex side panel

`python scripts/serve_desktop_panel.py` starts the real acceptance library and the production frontend without opening native windows. Open the URL from ignored `outputs/onboarding/panel-session.json` in the Codex right panel. It contains a local, per-session authorization token; do not publish it. The launcher uses ports 1420 and 18766 and fails if occupied. Browser import/export uses an in-page path form; search, playback and saved moments use the same backend as the native application. The native build retains Windows file dialogs. For UI tests while this frontend is open, set `FRAMEATLAS_UI_REUSE=1`.

## Operational limits

- Only Windows x64 is the current packaging target. macOS/Linux have not been packaged or verified.
- Indexing is visual. It does not transcribe speech, OCR documents, understand audio, or guarantee semantic correctness.
- Uniform sampling can miss scenes shorter than its interval. Increase sampling or vision detail when that tradeoff matters.
- Exact retrieval retains a matrix in memory (about 3 KB/vector before metadata). A library with one million frames needs several GB. There is no unmeasured billion-frame scale claim.
- File paths are authoritative. Moved/unplugged sources remain searchable from stored frames but cannot play/export until restored. Malformed media and full disks appear as job errors with retry.
- Search shares the encoder with background indexing and can wait for the active batch. CPU indexing is slower than real-time at detailed settings on this laptop.
