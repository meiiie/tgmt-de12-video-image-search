"""Uniform anchors plus frames near the beginning of detected shots."""
from bisect import bisect_right
from collections import deque
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

from .media import fingerprint

VERSION = "hybrid-v1"
SCENE_THRESHOLD = 10


def scene_cuts(path, cache: Path, current=lambda: True, progress=lambda seconds: None):
    stamp = fingerprint(Path(path))
    if cache.exists():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved["version"] == VERSION and saved["fingerprint"] == stamp:
            return saved["cuts"]
    import imageio_ffmpeg
    executable = Path(sys.executable).parent / "ffmpeg.exe"
    command = [str(executable) if executable.is_file() else imageio_ffmpeg.get_ffmpeg_exe(),
               "-hide_banner", "-nostdin", "-threads", "4", "-loglevel", "error", "-i", str(path),
               "-map", "0:v:0", "-an", "-sn", "-dn", "-vf",
               f"scale=160:-2,scdet=threshold={SCENE_THRESHOLD},metadata=mode=print:key=lavfi.scd.time:file=-:direct=1",
               "-progress", "pipe:2", "-f", "null", "-"]
    cuts, errors, reader_errors = [], deque(maxlen=20), []
    scanned = [0.0]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    def read_cuts():
        try:
            frame = None
            for line in process.stdout:
                match = re.match(r"frame:(\d+)\s+pts:\S+\s+pts_time:([\d.eE+-]+)", line)
                if match:
                    frame = {"frame": int(match[1]), "t": float(match[2])}
                elif line.startswith("lavfi.scd.time=") and frame is not None:
                    if frame["frame"] > 0 and math.isfinite(frame["t"]):
                        cuts.append(frame)
                    frame = None
        except Exception as error:
            reader_errors.append(error)

    def read_progress():
        try:
            for line in process.stderr:
                if line.startswith("out_time_us="):
                    value = line.strip().split("=", 1)[1]
                    if value.lstrip("-").isdigit():
                        scanned[0] = max(0, int(value) / 1_000_000)
                elif "=" not in line:
                    errors.append(line.strip())
        except Exception as error:
            reader_errors.append(error)

    readers = [threading.Thread(target=fn, daemon=True) for fn in (read_cuts, read_progress)]
    for reader in readers:
        reader.start()
    last_poll, last_progress, idle_seconds = time.monotonic(), -1.0, 0.0
    try:
        while process.poll() is None:
            if not current():
                raise InterruptedError("Đã dừng quét chuyển cảnh")
            now = time.monotonic()
            # Long media and a suspended laptop are legitimate. Only count active stalled polls.
            idle_seconds = 0.0 if scanned[0] != last_progress else idle_seconds + min(1.0, now - last_poll)
            last_poll, last_progress = now, scanned[0]
            if idle_seconds > 120:
                raise TimeoutError("Giải mã không tiến triển trong hai phút; hãy kiểm tra file nguồn")
            progress(scanned[0])
            time.sleep(.1)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for reader in readers:
            reader.join()
        process.stdout.close()
        process.stderr.close()
    if reader_errors:
        raise ValueError("Không đọc được kết quả quét chuyển cảnh") from reader_errors[0]
    if process.returncode:
        raise ValueError("Quét chuyển cảnh thất bại: " + "\n".join(errors)[-1500:])
    if not current():
        raise InterruptedError("Đã dừng quét chuyển cảnh")
    if fingerprint(Path(path)) != stamp:
        raise ValueError("Video thay đổi trong lúc quét; hãy quét lại thư viện")
    if any(b["frame"] <= a["frame"] or b["t"] <= a["t"] for a, b in zip(cuts, cuts[1:])):
        raise ValueError("Mốc chuyển cảnh không tăng dần")
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(".partial.json")
    temporary.write_text(json.dumps({"version": VERSION, "fingerprint": stamp, "cuts": cuts}), encoding="utf-8")
    temporary.replace(cache)
    progress(scanned[0])
    return cuts


def frame_plan(count, native_fps, fps, cuts):
    count = int(count)
    step = max(1, round(native_fps / fps))
    chosen = set(range(0, count, step))
    boundaries = [{"frame": 0, "t": 0.0}, *[c for c in cuts if 0 < c["frame"] < count],
                  {"frame": count, "t": count / native_fps}]
    for left, right in zip(boundaries, boundaries[1:]):
        begin, end = left["frame"], right["frame"]
        first_anchor = math.ceil(begin / step) * step
        early_end = min(end, begin + max(1, round(native_fps * .5)))
        if first_anchor >= early_end:
            chosen.add(min(end - 1, begin + min(round(native_fps * .2), (end - begin - 1) // 2)))
    starts = [b["frame"] for b in boundaries]
    result = []
    for frame in sorted(chosen):
        shot = bisect_right(starts, frame) - 1
        result.append({"frame": frame, "shot_start": boundaries[shot]["t"], "shot_end": boundaries[shot + 1]["t"]})
    return result


def signature(encoder_signature, settings):
    base = encoder_signature + f':fps={settings["fps"]}:pts-v1'
    return base + ":" + VERSION if settings["sampling"] == "hybrid" else base
