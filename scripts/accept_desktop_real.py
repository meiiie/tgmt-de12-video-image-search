"""Natural video + real EG2 acceptance using the bundled Python runtime."""
from pathlib import Path
import argparse
import json
import platform
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
from PIL import Image
from desktop.backend.library import Library
from desktop.backend.media import export_clip

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--data-dir", type=Path, default=root / "data/desktop-acceptance")
parser.add_argument("--report", type=Path, default=root / "outputs/onboarding/desktop-real-acceptance.json")
args = parser.parse_args()
data = args.data_dir
library = Library(data, start_worker=False)
library.settings({"model_path": str(root / "data/models/embeddinggemma-2"), "fps": .5, "vision_tokens": 140})
library.import_paths([str(root / "data/acceptance-media"), str(root / "data/smoke-9lxwfmyv/videos")])
started = time.perf_counter()
for video in library.store.videos():
    if video["status"] == "queued":
        library.index_video(video)
index_time = time.perf_counter() - started
assert all(v["status"] == "ready" for v in library.store.videos()), library.status()
queries = {}
for query in ["a bee on a flower", "con ong trên bông hoa", "a red square on a dark background"]:
    queries[query] = library.search(text=query)
    print(json.dumps({"query": query, "first": queries[query]["results"][0]["name"], "ms": queries[query]["elapsed_ms"]}, ensure_ascii=False), flush=True)
flower = next(v for v in library.store.videos() if v["name"] == "flower.mp4")
cap = cv2.VideoCapture(flower["path"])
cap.set(cv2.CAP_PROP_POS_MSEC, 2000)
ok, frame = cap.read()
cap.release()
assert ok
image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
image.save(root / "outputs/onboarding/flower-query.png")
queries["image at 2s"] = library.search(image=image)
assert queries["image at 2s"]["results"][0]["name"] == "flower.mp4"
assert queries["a bee on a flower"]["results"][0]["name"] == "flower.mp4"
moment_id = library.save_moment(flower["id"], 1, 3, 2, "Bee on flower · acceptance")
target = root / f"outputs/onboarding/flower-export-{int(time.time())}.mp4"
export_clip(flower, 1, 3, target)
cap = cv2.VideoCapture(str(target))
assert cap.read()[0]
duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
cap.release()
assert abs(duration - 2) < .1
library.close()
reopened = Library(data, start_worker=False)
assert any(m["id"] == moment_id for m in reopened.moments())
report = {"python": platform.python_version(), "index_seconds": index_time, "summary": reopened.status()["summary"], "model": reopened.encoder.signature, "queries": queries, "export": {"path": str(target), "duration": duration}, "restart_preserved": True, "source": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4", "scope": "integration acceptance on one natural and two synthetic videos; not an accuracy benchmark"}
args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
reopened.close()
print("ACCEPTANCE PASSED", flush=True)
