"""Five alternating real EG2 indexing pairs, then a complete ten-file index."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from desktop.backend.inference import Encoder
from desktop.backend.library import Library

WORK = ROOT / "outputs/review-20261114"
LIBRARY = ROOT / "data/desktop-acceptance"
settings = json.loads((WORK / "library-status.json").read_text(encoding="utf-8"))["settings"]

def measured_index(encoder, path, directory, prefetch):
    if (directory / 'library.sqlite3').exists():
        raise RuntimeError(f'Refusing a cached indexing measurement: {directory}')
    lib = Library(directory, encoder, start_worker=False)
    lib.store.update_settings({**settings, "batch_size": 4, "prefetch": prefetch, "paused": False})
    lib.import_paths([str(path)])
    begin = time.perf_counter()
    lib.index_video(lib.store.videos()[0])
    wall = time.perf_counter() - begin
    video = lib.store.videos()[0]
    assert video["status"] == "ready", video["error"]
    with lib.store.connect() as db:
        vectors = np.stack([np.frombuffer(r[0], dtype="float32") for r in db.execute("SELECT embedding FROM frames ORDER BY t")])
        times = [r[0] for r in db.execute("SELECT t FROM frames ORDER BY t")]
    lib.close()
    return {"video": path.name, "prefetch": prefetch, "wall_seconds": wall, "metrics": video,
            "timestamps": times}, vectors

def main():
    encoder = Encoder(WORK, settings["model_path"], settings["vision_tokens"])
    begin = time.perf_counter()
    encoder.ensure()
    print("Loaded", encoder.device, time.perf_counter()-begin, flush=True)
    from PIL import Image
    encoder.images([Image.new("RGB", (640,360), (50,70,100))]*4)
    report = {"settings": settings, "device": encoder.device, "pairs": []}
    inputs = sorted(Path(r"D:\TaiVe\TGMT\BTL\video\bo_thu_10_video").glob("*.mp4"))
    probe = WORK / "index-probe-40s.mp4"
    from desktop.backend.media import run_ffmpeg
    run_ffmpeg(["-y", "-i", str(inputs[0]), "-t", "40", "-an", "-c:v", "copy", str(probe)])
    for n in range(5):
        vectors = {}
        timestamps = {}
        for prefetch in (False, True):
            result, vector = measured_index(encoder, probe, WORK / f"pairs/{n}-{prefetch}", prefetch)
            vectors[prefetch] = vector
            timestamps[prefetch] = result['timestamps']
            report["pairs"].append(result)
            print("Pair", n, prefetch, round(result["wall_seconds"],3), flush=True)
        agreement = np.sum(vectors[False]*vectors[True],axis=1)
        assert np.allclose(vectors[False], vectors[True], atol=2e-4), agreement.min()
        assert timestamps[False] == timestamps[True]
        (WORK / "index-comparison.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    # Complete measurements include the three originals, not just the added short clips.
    with sqlite3.connect((LIBRARY/'library.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        sources=[Path(r[0]) for r in db.execute("SELECT path FROM videos ORDER BY added")]
    assert len(sources)==10
    if (WORK / 'measured-library/library.sqlite3').exists():
        raise RuntimeError('Full measurement must start from an empty index')
    full = Library(WORK / "measured-library", encoder, start_worker=False)
    full.store.update_settings({**settings,"batch_size":4,"prefetch":True,"paused":False})
    full.import_paths([str(p) for p in sources])
    for video in reversed(full.store.videos()):
        full.index_video(video)
        status=next(v for v in full.store.videos() if v["id"]==video["id"])
        assert status["status"]=="ready",status
        print("Full",status["name"][:36],status["frames"],round(status["index_seconds"],2),flush=True)
        (WORK / "index-ten-videos.json").write_text(json.dumps(full.status(),ensure_ascii=False,indent=2),encoding="utf-8")
    full.close()

if __name__ == "__main__":
    main()
