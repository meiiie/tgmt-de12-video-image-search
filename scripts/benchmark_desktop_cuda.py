"""Compare CUDA EG2 vectors with committed CPU vectors from the same video frames."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.site.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import cv2
    import numpy as np
    from PIL import Image
    import torch
    from desktop.backend.inference import Encoder

    assert torch.cuda.is_available(), "CUDA distribution/driver is not available"
    assert torch.cuda.is_bf16_supported(), "This probe requires native BF16 support"
    with sqlite3.connect(args.library.resolve().as_uri() + "?mode=ro", uri=True) as db:
        settings = {key: json.loads(value) for key, value in db.execute("SELECT key,value FROM settings")}
        source, identity = db.execute("SELECT path,id FROM videos ORDER BY frames DESC LIMIT 1").fetchone()
        records = db.execute("SELECT t,embedding FROM frames WHERE video_id=? ORDER BY t LIMIT 12", (identity,)).fetchall()
    assert len(records) == 12, "Need 12 committed CPU frames"
    images = []
    cap = cv2.VideoCapture(source)
    for t, _ in records:
        assert cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        assert ok and abs(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - t) < .02
        images.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    cap.release()
    cpu = np.stack([np.frombuffer(blob, dtype="float32") for _, blob in records])
    encoder = Encoder(args.output, settings["model_path"], settings["vision_tokens"])
    started = time.perf_counter()
    encoder.ensure()
    load_seconds = time.perf_counter() - started
    measurements, vectors = [], []
    for offset in range(0, len(images), 4):
        torch.cuda.synchronize()
        started = time.perf_counter()
        batch = encoder.images(images[offset:offset + 4])
        torch.cuda.synchronize()
        measurements.append(time.perf_counter() - started)
        vectors.extend(batch)
    gpu = np.stack(vectors)
    cosine = np.sum(cpu * gpu, axis=1) / (np.linalg.norm(cpu, axis=1) * np.linalg.norm(gpu, axis=1))
    report = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(), "dtype": str(next(encoder.model.parameters()).dtype), "load_seconds": load_seconds, "batch_size": 4, "vision_tokens": settings["vision_tokens"], "batch_seconds": measurements, "frames_per_second_after_first_batch": 8 / sum(measurements[1:]), "cpu_gpu_cosine": cosine.tolist(), "gpu_norms": np.linalg.norm(gpu, axis=1).tolist(), "max_vector_absolute_difference": float(np.max(np.abs(cpu - gpu))), "peak_allocated_mb": torch.cuda.max_memory_allocated() / 2**20, "peak_reserved_mb": torch.cuda.max_memory_reserved() / 2**20}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "cuda-comparison.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)
    assert np.isfinite(gpu).all() and cosine.min() >= .99, "GPU vectors differ materially from CPU reference"


if __name__ == "__main__":
    main()
