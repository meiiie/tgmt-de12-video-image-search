import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid
import math

import cv2
from PIL import Image

EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mts"}
_preview_lock = threading.Lock()


def decode_batch(cap, plan, cursor, batch_size, native_fps, decoder_next):
    images, times, locations = [], [], []
    for location in plan[cursor:cursor + batch_size]:
        i = location["frame"]
        if i < decoder_next or i - decoder_next >= native_fps * 2:
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, i):
                raise ValueError("Không thể đọc chính xác mốc video; thử mức lấy mẫu dày hơn")
        else:
            for _ in range(i - decoder_next):
                if not cap.grab():
                    raise ValueError("Video bị ngắt hoặc lỗi giải mã giữa chừng")
        ok, frame = cap.read()
        if not ok:
            raise ValueError("Video bị ngắt hoặc lỗi giải mã giữa chừng")
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if not math.isfinite(timestamp) or (i > 0 and timestamp <= 0):
            raise ValueError("Video không cung cấp mốc thời gian giải mã hợp lệ")
        if location["shot_start"] is not None and not location["shot_start"] - .05 <= timestamp < location["shot_end"] + .05:
            raise ValueError("Mốc chuyển cảnh và giải mã không khớp; hãy thử lấy mẫu đều")
        images.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        times.append(round(timestamp, 6))
        locations.append(location)
        decoder_next = i + 1
        cursor += 1
    return images, times, locations, cursor, decoder_next


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
