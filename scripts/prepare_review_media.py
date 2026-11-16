"""Prepare seven non-overlapping public-film excerpts for the ten-file app check."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "outputs/review-20261114"
TARGET = Path(r"D:\TaiVe\TGMT\BTL\video\bo_thu_10_video")
FFMPEG = ROOT / "desktop/runtime314/ffmpeg.exe"
TARGET.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
bunny = WORK / "bunny-original.m4v"
if not bunny.exists():
    archive = WORK / "bunny.zip"
    url = "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_640x360.m4v.zip"
    urllib.request.urlretrieve(url, archive)
    with ZipFile(archive) as z:
        name = next(n for n in z.namelist() if n.endswith(".m4v"))
        bunny.write_bytes(z.read(name))
sources = {
    "Bunny": str(bunny),
    "Elephants": "https://download.blender.org/ED/elephantsdream-480-h264-st-aac.mov",
    "Caminandes": str(WORK / "caminandes-original.mp4"),
    "Tears": "https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov",
}
caminandes = WORK / "caminandes-original.mp4"
if not caminandes.exists():
    archive = WORK / "caminandes.zip"
    urllib.request.urlretrieve("https://download.blender.org/demo/movies/caminandes_gran_dillama.mp4.zip", archive)
    with ZipFile(archive) as z:
        name = next(n for n in z.namelist() if n.endswith(".mp4"))
        caminandes.write_bytes(z.read(name))
clips = [
    ("Bunny", 35), ("Bunny", 215), ("Elephants", 35), ("Elephants", 215),
    ("Caminandes", 0), ("Tears", 45), ("Tears", 245),
]

def create_clip(item):
    index, (source, start) = item
    seconds = 146 if source == "Caminandes" else 150
    path = TARGET / f"{index+1:02}_{source}_{start}s_{seconds}s.mp4"
    if not path.exists():
        args = [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
        if sources[source].startswith("https:"):
            args += ["-rw_timeout", "30000000"]
        args += ["-ss", str(start), "-i", sources[source], "-t", str(seconds), "-map", "0:v:0",
                 "-an", "-vf", "scale=640:-2,fps=25", "-c:v", "libx264", "-threads", "2",
                 "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                 str(path.with_suffix(".partial.mp4"))]
        for attempt in range(3):
            result = subprocess.run(args, capture_output=True, timeout=600)
            if result.returncode == 0:
                path.with_suffix(".partial.mp4").replace(path)
                break
        else:
            raise RuntimeError(result.stderr.decode(errors="replace")[-1000:])
    import cv2
    cap = cv2.VideoCapture(str(path))
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    assert seconds - 1 < duration < seconds + 1, (path, duration)
    print(path.name, round(duration, 2), flush=True)
    original_url = {"Bunny": "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_640x360.m4v.zip",
                    "Caminandes": "https://download.blender.org/demo/movies/caminandes_gran_dillama.mp4.zip"}
    return {"path": str(path), "source": source, "source_url": original_url.get(source, sources[source]),
            "source_start": start, "seconds": duration, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

with ThreadPoolExecutor(max_workers=2) as pool:
    entries = list(pool.map(create_clip, enumerate(clips)))
(WORK / "media-manifest.json").write_text(json.dumps(
    {"description": "Six non-overlapping 150-second excerpts and one 146-second excerpt from four Blender Open Movie sources; ten library files are not ten independent recordings.",
     "videos": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
