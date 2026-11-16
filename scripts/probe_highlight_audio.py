"""Local EG2 audio retrieval experiment; candidates are NOT approved highlights.

Uses ESC-50 fold 1 as a small labeled sanity check, then ranks non-overlapping
10-second audio windows from a local video. Does not change the app/library.
ESC-50 is CC BY-NC 3.0; downloaded audio and its attribution stay in outputs.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

import numpy as np

ESC_REVISION = "33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6"
ESC_BASE = f"https://raw.githubusercontent.com/karolpiczak/ESC-50/{ESC_REVISION}/"
CLASSES = {
    "laughing": "People laughing.",
    "clapping": "People clapping their hands.",
    "crying_baby": "A baby crying.",
    "coughing": "A person coughing.",
}
QUERIES = {
    "laugh_en": "People laughing.",
    "laugh_vi": "Mọi người đang cười lớn.",
    "excited_en": "People shouting excitedly and celebrating.",
    "argument_vi": "Nhiều người đang tranh luận gay gắt.",
    "music_en": "Music playing.",
    "funny_vi": "Khoảnh khắc hài hước nhất trong video.",
}


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def download(relative, path):
    if not path.exists():
        with urlopen(ESC_BASE + relative, timeout=90) as response:
            data = response.read()
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)


def decode(ffmpeg, source, destination=None):
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(source),
               "-map", "0:a:0", "-vn", "-ac", "1", "-af", "aresample=16000:async=1:first_pts=0",
               "-f", "s16le"]
    if destination:
        temporary = destination.with_suffix(".tmp")
        subprocess.run(command + ["-y", str(temporary)], check=True)
        temporary.replace(destination)
    else:
        result = subprocess.run(command + ["pipe:1"], check=True, capture_output=True)
        return np.frombuffer(result.stdout, dtype="<i2").astype(np.float32) / 32768


def normalize(vectors):
    values = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if values.shape[1] != 768 or not np.isfinite(values).all() or np.any(norms < 1e-9):
        raise ValueError("Expected finite, nonzero 768-dimensional EG2 vectors")
    return values / norms


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-windows", type=int, default=0, help="0 means all; checkpoints resume")
    args = parser.parse_args()
    if args.max_windows < 0:
        parser.error("--max-windows must be >= 0")
    args.output.mkdir(parents=True, exist_ok=True)
    source_stat = args.source.stat()
    signature = {
        "source": str(args.source.resolve()), "size": source_stat.st_size,
        "mtime_ns": source_stat.st_mtime_ns, "model": str(args.model.resolve()),
        "config_sha256": hashlib.sha256((args.model / "config.json").read_bytes()).hexdigest(),
        "weights": [(p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(args.model.glob("*.safetensors"))],
        "sample_rate": 16000, "window_seconds": 10, "dtype": "bfloat16", "schema": 1,
    }
    signature = json.loads(json.dumps(signature))
    manifest_path = args.output / "input.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")) != signature:
        raise ValueError("Different source/model: use a new output folder")
    save_json(manifest_path, signature)

    controls = args.output / "esc50"
    controls.mkdir(exist_ok=True)
    download("meta/esc50.csv", controls / "metadata.csv")
    download("LICENSE", controls / "LICENSE.txt")
    rows = [r for r in csv.DictReader(io.StringIO((controls / "metadata.csv").read_text()))
            if r["fold"] == "1" and r["category"] in CLASSES]
    rows.sort(key=lambda r: r["filename"])
    assert len(rows) == 32, f"Unexpected ESC-50 selection: {len(rows)}"
    for row in rows:
        download("audio/" + row["filename"], controls / row["filename"])
    print(json.dumps({"stage": "control_data", "clips": len(rows)}), flush=True)

    pcm = args.output / "source.s16le"
    if not pcm.exists():
        decode(args.ffmpeg, args.source, pcm)
    audio = np.memmap(pcm, mode="r", dtype="<i2")
    duration = len(audio) / 16000
    total = (len(audio) + 159999) // 160000
    limit = min(total, args.max_windows or total)
    print(json.dumps({"stage": "decoded", "audio_seconds": duration, "windows": total}), flush=True)

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    import torch
    from sentence_transformers import SentenceTransformer
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(), "Probe requires BF16 CUDA"
    torch.set_num_threads(4)
    started = time.perf_counter()
    model = SentenceTransformer(str(args.model), device="cuda", local_files_only=True,
        config_kwargs={"vision_config": None}, model_kwargs={"dtype": torch.bfloat16})
    load_seconds = time.perf_counter() - started

    def embed_audio(samples):
        return normalize(model.encode([{"audio": {"array": samples, "sampling_rate": 16000}}],
            normalize_embeddings=True, show_progress_bar=False))

    control_path = controls / "vectors.npy"
    if control_path.exists():
        control_vectors = np.load(control_path)
    else:
        control_vectors = np.concatenate([embed_audio(decode(args.ffmpeg, controls / r["filename"])) for r in rows])
        np.save(control_path, control_vectors)
    labels = list(CLASSES)
    query_vectors = normalize(model.encode(list(CLASSES.values()) + list(QUERIES.values()),
        prompt_name="SearchQuery", normalize_embeddings=True, show_progress_bar=False))
    control_scores = control_vectors @ query_vectors[:len(labels)].T
    predicted = control_scores.argmax(axis=1)
    control_report = {
        "dataset_revision": ESC_REVISION, "selection": "all fold-1 clips in 4 preselected categories",
        "license": "CC BY-NC 3.0; see esc50/LICENSE.txt for per-file attribution",
        "samples": len(rows), "correct": sum(labels[int(p)] == r["category"] for p, r in zip(predicted, rows)),
        "items": [{"file": r["filename"], "truth": r["category"], "predicted": labels[int(p)]}
                  for r, p in zip(rows, predicted)],
        "laughter_queries": {},
        "limitations": "Small closed set; related takes may share source recordings; no stream speech/music negatives. Not a humor test or independent model-training holdout.",
    }
    for qid in ("laugh_en", "laugh_vi"):
        q = query_vectors[len(labels) + list(QUERIES).index(qid)]
        order = np.argsort(-(control_vectors @ q))
        truth = np.array([rows[int(i)]["category"] == "laughing" for i in order])
        precision = np.cumsum(truth) / np.arange(1, len(truth) + 1)
        control_report["laughter_queries"][qid] = {
            "precision_at_5": float(truth[:5].mean()), "average_precision": float(precision[truth].mean()),
            "ranked_files": [rows[int(i)]["filename"] for i in order],
        }
    save_json(args.output / "control-report.json", control_report)
    print(json.dumps({"stage": "control_done", "correct": control_report["correct"], "total": len(rows),
        "laughter": {k: {m: v[m] for m in ("precision_at_5", "average_precision")} for k, v in control_report["laughter_queries"].items()}}), flush=True)

    cache = args.output / "audio-vectors.npz"
    if cache.exists():
        with np.load(cache) as checkpoint:
            vectors, timings = list(checkpoint["vectors"]), list(checkpoint["seconds"])
    else:
        vectors, timings = [], []
    initial_count = len(vectors)
    for index in range(initial_count, limit):
        samples = np.asarray(audio[index * 160000:(index + 1) * 160000], dtype=np.float32) / 32768
        torch.cuda.synchronize()
        start = time.perf_counter()
        vector = embed_audio(samples)[0]
        torch.cuda.synchronize()
        vectors.append(vector)
        timings.append(time.perf_counter() - start)
        if len(vectors) % 20 == 0 or len(vectors) == limit:
            temporary = cache.with_suffix(".tmp.npz")
            np.savez(temporary, vectors=np.stack(vectors), seconds=np.array(timings))
            temporary.replace(cache)
            print(json.dumps({"stage": "audio_index", "done": len(vectors), "total": total,
                "last_window_seconds": round(timings[-1], 3)}), flush=True)

    matrix = np.stack(vectors)
    result = {"audio_seconds": duration, "indexed_seconds": min(len(vectors) * 10, duration),
        "windows": len(vectors), "total_windows": total, "complete": len(vectors) == total,
        "model_load_seconds_this_run": load_seconds, "index_seconds_sum": float(sum(timings)),
        "new_windows_this_run": len(vectors) - initial_count, "torch": torch.__version__,
        "peak_cuda_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
        "queries": [], "human_review": "pending; similarity is not humor, virality or calibrated confidence"}
    for qi, (qid, text) in enumerate(QUERIES.items()):
        scores = matrix @ query_vectors[len(labels) + qi]
        selected = []
        for index in np.argsort(-scores):
            start = int(index) * 10
            if all(abs(start - item["signal_start"]) >= 30 for item in selected):
                selected.append({"signal_start": start, "signal_end": min(start + 10, duration),
                    "review_start": max(0, start - 15), "review_end": min(duration, start + 25),
                    "similarity": float(scores[index]), "status": "unreviewed"})
                if len(selected) == 10:
                    break
        result["queries"].append({"id": qid, "text": text, "results": selected})
    final_stat = args.source.stat()
    assert (source_stat.st_size, source_stat.st_mtime_ns) == (final_stat.st_size, final_stat.st_mtime_ns)
    result["source_unchanged"] = True
    save_json(args.output / "candidates.json", result)
    print(json.dumps({"stage": "complete", "windows": len(vectors), "seconds": result["index_seconds_sum"],
        "peak_cuda_mib": result["peak_cuda_allocated_mib"], "fully_indexed": result["complete"]}), flush=True)


if __name__ == "__main__":
    main()
