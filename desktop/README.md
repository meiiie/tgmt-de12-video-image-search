# FrameAtlas for Windows

FrameAtlas finds moments in local video files using text or an image. It opens the source at the matching time, saves named intervals and exports accurate, re-encoded MP4 clips. Original videos are never moved or deleted.

## First launch

For the portable build, extract the entire ZIP, then open `FrameAtlas/frameatlas.exe`. Keep the adjacent `runtime` and `engine` directories with it. No system Python installation is needed. The application still stores its library under the per-user data directory, so moving the extracted program does not move your catalog.

1. Launch the Windows build. The native shell starts and owns its local worker automatically.
2. Open **Cài đặt** to select an existing EmbeddingGemma 2 directory, or leave the path empty to download the official pinned weights. The first download needs roughly 1.5 GB plus tokenizer files. Loading text and vision uses additional memory; 16 GB RAM is recommended for this CPU build.
3. Choose **Thêm video** or **Thêm thư mục**. Dragging files/folders into the native window also imports them. Folder imports include supported videos in subfolders.
4. Search while completed batches become available. Use Vietnamese or English, or upload a PNG/JPEG/WebP query. `Ctrl+K` returns to text entry; `Escape` closes the inspector.
5. Select a result, play the video, adjust start/end in seconds, and save or export the interval. Export requires a new `.mp4` filename and never overwrites an existing file.

Image queries now show the reference image before searching. Drag a rectangle over the detail you want, or open **Chọn vùng bằng bàn phím** for percentage controls, then choose **Dùng vùng đã chọn**. The selected crop is shown separately; **Dùng toàn ảnh** restores the original. A pending selection disables search until applied or reset, and changing the image clears old results. The image API respects EXIF orientation. Cropping changes what is being searched for; it is not a guarantee of higher retrieval accuracy. See [the input checks and real-video evidence](../docs/image-search-practical-workflow.md).

**Cách tìm ảnh** offers two modes. **Nội dung tương tự** keeps semantic image search, including changed viewpoints. **Đối chiếu chi tiết ảnh** checks local feature geometry and appearance in up to 48 EG2 candidates; use it to recover a screenshot or a sufficiently detailed crop. It may reject a valid object after motion, occlusion or a viewpoint change. An empty result means insufficient evidence among the checked candidates, not confirmed absence from the video. The displayed detail result is a short viewing interval around a checked frame, not an annotation of its entire appearance. Text search remains available independently.

**Hoạt động** exposes progress, pause, resume, cancel and retry. Pause takes effect at the next inference-batch boundary. **Quét thay đổi** checks imported folders and known files for additions/changes; it is an explicit scan, not an operating-system watcher. Removing a library entry removes its saved moments/index only. A later scan of its tracked folder can discover that source again; stop tracking the folder to prevent that.

**Lần xuất hiện** is available when a single video is selected. It identifies candidate events from similarity peaks, not a guaranteed count of real-world actions. No nth candidate means no result.

For long recordings, Settings offers **0.1 fps — mỗi 10 giây** for a first pass. Activity shows processed video time, throughput and an estimated remaining time. Sampling can miss brief scenes between frames; use a denser setting when those scenes matter. Changing sampling rebuilds the index. Choose a single video in **Phạm vi**, then enter **Từ phút / Đến phút** to search within a known interval; decimal minutes are supported and blank fields mean the beginning/end of the video.

Under **Cách lấy khung hình**, **Mốc đều + bổ sung khi chuyển cảnh** retains all regular samples and adds an early frame when a detected shot's beginning is not covered. The extra scan decodes the whole video once and can be paused/cancelled. Its completed cut cache is reused on a retry. This helps with shot changes between regular samples; an object briefly entering the same continuous shot can still be missed. Changing this setting rebuilds frame embeddings while preserving saved moments. Hybrid search uses actual timestamps and clips proposed intervals to detected shot boundaries. See [the sampling and verification measurements](../docs/sampling-and-verification-20261102.md).

The real-video check covers a 2-hour-11-minute 1080p recording, restart recovery, Vietnamese visual retrieval, silent seek, saved intervals and an actual 5-second export. See [the evidence and limitations](../docs/real-video-acceptance.md).

## Thống kê tìm kiếm và thời gian lập chỉ mục

Kết quả ảnh có bảng theo từng video: số khung đã so, số khung qua ngưỡng cosine, điểm cao nhất và, ở chế độ chi tiết, số khung đã đối chiếu/khớp. Số qua ngưỡng được đếm trước khi giới hạn danh sách kết quả; các khung liên tiếp có thể gộp thành một khoảnh khắc. Đây là số ứng viên theo cấu hình đang chọn, không phải số lần xuất hiện đã được xác nhận bằng nhãn.

Thư viện hiển thị số khung được đo, tổng thời gian và thời gian đọc khung, chạy EG2, lưu chỉ mục. Cài đặt **Đọc trước một lô khung** cho phép giải mã lô kế tiếp trong khi xử lý lô hiện tại. Một worker vẫn xử lý lần lượt các video. Tìm kiếm chấm điểm trên ma trận vector đã lưu, không mở lại từng video; các yêu cầu tìm được giữ theo lượt. Xem [số liệu lịch sử ngày 14/11/2026](../results/review-20261114/README.md) để phân biệt phép đo cũ với kết quả hiện tại.

## Data and offline use

The per-user data directory is shown in Settings (normally `%APPDATA%\app.frameatlas.desktop`). It contains `library.sqlite3`, thumbnails, 960-pixel detail images, completed scene-cut caches, compatible preview copies, downloaded models, `worker.log` and one previous log. Detail images add disk usage to new indexes. Old indexes can decode original frames on demand when those images are missing. Copy the whole directory with the app closed to back it up. Keep original videos at their recorded paths. The app does not upload videos, queries or usage analytics. The first model download contacts Hugging Face; subsequent automatic loads use the completed local model.

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
node node_modules/@tauri-apps/cli/tauri.js build
# Compile application/resources for a portable ZIP without NSIS compression:
node node_modules/@tauri-apps/cli/tauri.js build --no-bundle
```

Installer output: `desktop/src-tauri/target/release/bundle/nsis/`. The build is unsigned unless a signing identity is supplied by the distributor. The unbundled executable needs the adjacent `runtime` and `engine` resource folders.

After the native release build, `desktop/runtime314/python.exe scripts/package_portable.py` (from the repository root) creates a ZIP under `outputs/releases/` and verifies its CRC. The portable package omits Python bytecode and C++ build headers. Verify a freshly extracted copy with `scripts/verify_desktop_package.py --build-dir <extracted-FrameAtlas-directory> --report <report.json>` using the bundled Python interpreter and the acceptance inputs below.

An optional CUDA 12.6 variant uses the same application and engine with official `torch==2.14.1+cu126` and `torchvision==0.29.1+cu126` wheels. Install them into a separate directory, verify with `scripts/benchmark_desktop_cuda.py`, then assemble with `scripts/build_cuda_variant.py --site <wheel-install-directory> --output <fresh-directory>`. The script keeps the CPU runtime intact and runs dependency/device checks. Package the variant with `scripts/package_portable.py --build-dir <variant-directory> --name FrameAtlas_0.1.0_windows-x64-cuda126-portable`. Its larger runtime is intended for compatible NVIDIA machines; validation here covers the RTX 3050 Ti and driver recorded in the real-video report.

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
- Hybrid sampling depends on detected visual cuts; it is not object tracking. Repeated game backgrounds or HUD elements can match across unrelated moments. Inspect the returned frame and use a focused crop when that is the intended search.
- Exact retrieval retains a matrix in memory (about 3 KB/vector before metadata). A library with one million frames needs several GB. There is no unmeasured billion-frame scale claim.
- File paths are authoritative. Moved/unplugged sources remain searchable from stored frames but cannot play/export until restored. Malformed media and full disks appear as job errors with retry.
- Search shares the encoder with background indexing and can wait for the active batch. CPU indexing is slower than real-time at detailed settings on this laptop.
