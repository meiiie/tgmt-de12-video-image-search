"""Compare supported EG2 vision budgets on identical inputs; not an accuracy benchmark."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image
from desktop.backend.inference import Encoder

root = Path(__file__).resolve().parents[1]
encoder = Encoder(root / "data/vision-profile", str(root / "data/models/embeddinggemma-2"))
encoder.ensure()
images = [Image.open(root / "data/smoke-9lxwfmyv/query.png"), Image.new("RGB", (640, 360), "blue")]
text = encoder.query(text="a red square on a dark background")
report = []
baseline = None
for tokens in [280, 140, 70]:
    times = []
    for repeat in range(3):
        started = time.perf_counter()
        vectors = encoder.model.encode([{"image": image} for image in images], normalize_embeddings=True, batch_size=2, show_progress_bar=False, processing_kwargs={"image": {"max_soft_tokens": tokens}})
        times.append(time.perf_counter() - started)
    if baseline is None:
        baseline = vectors
    item = {"tokens": tokens, "seconds_batch2": times, "cosine_to_280": np.sum(vectors * baseline, axis=1).tolist(), "text_scores": (vectors @ text).tolist(), "finite": bool(np.isfinite(vectors).all())}
    report.append(item)
    print(json.dumps(item), flush=True)
(root / "outputs/onboarding/eg2-vision-profile.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
