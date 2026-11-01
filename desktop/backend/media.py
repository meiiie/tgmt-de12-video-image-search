import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

import cv2

EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mts"}
_preview_lock = threading.Lock()


def fingerprint(path: Path):
    stat = path.stat()
    digest = hashlib.sha256(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
    with path.open("rb") as file:
        digest.update(file.read(65536))
        file.seek(max(0, stat.st_size - 65536))
        digest.update(file.read(65536))
    return digest.hexdigest()


def run_ffmpeg(arguments):
    import imageio_ffmpeg
    packaged = Path(sys.executable).parent / "ffmpeg.exe"
    result = subprocess.run(
        [str(packaged) if packaged.is_file() else imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", *arguments],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace")[-1500:])


def preview_path(video, root):
    source = Path(video["path"])
    if not source.is_file():
        raise FileNotFoundError("Không tìm thấy file nguồn. Hãy kết nối lại ổ đĩa hoặc làm mới thư viện.")
    cap = cv2.VideoCapture(str(source))
    code = int(cap.get(cv2.CAP_PROP_FOURCC))
    cap.release()
    codec = "".join(chr((code >> 8 * i) & 255) for i in range(4)).lower()
    if source.suffix.lower() in {".mp4", ".m4v"} and codec in {"avc1", "h264"}:
        return source
    target = root / "previews" / f'{video["id"]}-{video["fingerprint"][:12]}.mp4'
    with _preview_lock:
        if not target.exists():
            temporary = target.with_suffix(".partial.mp4")
            run_ffmpeg(["-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-movflags", "+faststart", str(temporary)])
            temporary.replace(target)
    return target


def export_clip(video, start, end, target: Path):
    source = Path(video["path"])
    if not source.is_file():
        raise FileNotFoundError("File video nguồn không còn ở vị trí đã nhập")
    if start < 0 or end <= start or end > video["duration"] + 0.1:
        raise ValueError("Khoảng xuất không hợp lệ")
    if not target.is_absolute():
        raise ValueError("Nhập đường dẫn đầy đủ đến file MP4 đích")
    if target.suffix.lower() != ".mp4" or target.exists() or target.resolve() == source.resolve():
        raise ValueError("Chọn tên file .mp4 mới; không ghi đè file có sẵn")
    if not target.parent.is_dir():
        raise ValueError("Thư mục đích không tồn tại")
    temporary = target.parent / f".frameatlas-{uuid.uuid4().hex}.mp4"
    try:
        run_ffmpeg(["-n", "-ss", str(start), "-i", str(source), "-t", str(end - start), "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-movflags", "+faststart", str(temporary)])
        # Windows rename refuses an existing destination and also works on exFAT.
        if os.name == "nt":
            temporary.rename(target)
        else:
            os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)
