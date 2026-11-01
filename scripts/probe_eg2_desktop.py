"""Real EG2 integration evidence. Synthetic media is not a retrieval benchmark."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop.backend.inference import Encoder
from desktop.backend.library import Library

root = Path(__file__).resolve().parents[1]
data = root / "data" / "desktop-real"
library = Library(data, Encoder(data, str(root / "data/models/embeddinggemma-2")), start_worker=False)
started = time.perf_counter()
library.encoder.ensure()
load_seconds = time.perf_counter() - started
source = root / "data/smoke-9lxwfmyv/videos"
library.import_paths([str(source)])
started = time.perf_counter()
for video in library.store.videos():
    if video["status"] == "queued":
        library.index_video(video)
index_seconds = time.perf_counter() - started
from PIL import Image
image = Image.open(root / "data/smoke-9lxwfmyv/query.png")
queries = {}
for name, kwargs in [("image", {"image": image}), ("text", {"text": "a red square on a dark background"}), ("text_cached", {"text": "a red square on a dark background"})]:
    queries[name] = library.search(**kwargs)
report = {"model": library.encoder.signature, "load_seconds": load_seconds, "index_seconds": index_seconds, "status": library.status(), "queries": queries}
destination = root / "outputs/onboarding/desktop-eg2.json"
destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"load_seconds": load_seconds, "index_seconds": index_seconds, "videos": report["status"]["summary"], "queries": {key: {"elapsed_ms": value["elapsed_ms"], "results": len(value["results"])} for key, value in queries.items()}}, indent=2), flush=True)
library.close()
