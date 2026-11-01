"""Measure image retrieval misses, absent-query false accepts and preprocessing ablations.

Uses a separate desktop library, real EG2, and the production temporal retrieval code.
All generated media/embeddings stay in ignored data/ or outputs/ directories.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import cv2
import numpy as np
from PIL import Image

from desktop.backend.inference import Encoder, MODEL_ID, REVISION
from desktop.backend.library import Library
from desktop.backend.store import Store
from retrieval_quality_metrics import calibrate, peak_matches, summarize
from vsearch.text import text_search


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_indices(frames, fps, native_fps):
    step = round(native_fps / fps)
    return [i for i, f in enumerate(frames) if round(f["t"] * native_fps) % step == 0]


def rank(frames, scores, fps, durations, limit):
    hits = text_search(frames, None, None, fps, scores=scores, k=limit, w=1)
    for hit in hits:
        hit["end"] = min(hit["end"], durations[hit["video"]])
    return hits


def build_embeddings(args, manifest):
    if (args.output / "library").exists():
        raise ValueError("Use a fresh output folder; --score-only reuses a completed embedding run")
    started = time.perf_counter()
    protocol = manifest["protocol"]
    packages = {name: importlib.metadata.version(name) for name in ("torch", "transformers", "sentence-transformers", "numpy")}
    # OpenCV can be installed as opencv-python or opencv-python-headless.
    packages["opencv_runtime"] = cv2.__version__
    library_root = args.output / "library"
    Store(library_root).update_settings({"fps": 2.0, "batch_size": 4,
        "model_path": str(args.model.resolve()), "vision_tokens": protocol["vision_tokens"]})
    encoder = Encoder(library_root, str(args.model.resolve()), protocol["vision_tokens"])
    library = Library(library_root, encoder=encoder, start_worker=False)
    imported = library.import_paths([str((args.dataset / "videos" / v["name"]).resolve()) for v in manifest["videos"]])
    assert not imported["errors"], imported
    for video in library.store.videos():
        print(f"Indexing {video['name']}", flush=True)
        library.index_video(video)
        complete = library.store.video(video["id"])
        assert complete["status"] == "ready", complete["error"]
    with library.store.connect() as db:
        rows = db.execute("SELECT f.t,f.embedding,v.name,v.id FROM frames f JOIN videos v ON v.id=f.video_id ORDER BY v.id,f.t").fetchall()
    frames = [{"video": r["name"], "t": r["t"], "kind": "frame"} for r in rows]
    vectors = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
    for spec in manifest["videos"]:
        actual = [f["t"] for f in frames if f["video"] == spec["name"]]
        expected = np.arange(0, spec["frames"], 12) / protocol["fps"]
        np.testing.assert_allclose(actual, expected, atol=1e-6, rtol=0)
    queries = manifest["queries"]
    query_vectors = []
    for index, query in enumerate(queries):
        # Match interactive query encoding; mixed-aspect BF16 batches can change near ties.
        with Image.open(args.dataset / query["image"]) as image:
            query_vectors.append(encoder.query(image=image.convert("RGB")))
        if index % 40 == 0:
            print(f"Query images {index + 1}/{len(queries)}", flush=True)
    query_vectors = np.stack(query_vectors)
    region_indices = sample_indices(frames, 1, protocol["fps"])
    region_vectors = []
    for count, index in enumerate(region_indices):
        frame = frames[index]
        cap = cv2.VideoCapture(str(args.dataset / "videos" / frame["video"]))
        try:
            assert cap.set(cv2.CAP_PROP_POS_FRAMES, round(frame["t"] * protocol["fps"]))
            ok, bgr = cap.read()
            assert ok
            assert abs(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - frame["t"]) < 1e-5
        finally:
            cap.release()
        image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        w, h = image.size
        crops = [image.crop((x0, y0, x1, y1)) for x0, y0, x1, y1 in
                 [(0, 0, w//2, h//2), (w//2, 0, w, h//2), (0, h//2, w//2, h), (w//2, h//2, w, h)]]
        region_vectors.append(encoder.images(crops))
        if count % 10 == 0:
            print(f"Region frames {count + 1}/{len(region_indices)}", flush=True)
    durations = {v["name"]: v["duration"] for v in manifest["videos"]}
    for array in (vectors, query_vectors, np.asarray(region_vectors)):
        assert np.isfinite(array).all()
        np.testing.assert_allclose(np.linalg.norm(array, axis=-1), 1, atol=1e-5)
    # Keep expensive real embeddings even if a later validation/report step fails.
    np.savez_compressed(args.output / "embeddings.npz", frames=vectors, queries=query_vectors, regions=np.stack(region_vectors))
    parity = []
    for query in [q for q in queries if q["kind"] == "object" and q["padding"] == .15][::40]:
        qi = queries.index(query)
        with Image.open(args.dataset / query["image"]) as image:
            result = library.search(image=image.convert("RGB"), limit=protocol["max_results"])["results"]
        cached = rank(frames, vectors @ query_vectors[qi], 2, durations, protocol["max_results"])
        assert [(r["name"], r["peak"]) for r in result] == [(r["video"], r["peak_t"]) for r in cached]
        np.testing.assert_allclose([r["score"] for r in result], [r["score"] for r in cached], atol=1e-6, rtol=0)
        parity.append(query["id"])
    language = []
    for query in protocol["natural_language_checks"]:
        results = library.search(text=query["text"], limit=10)["results"]
        hits = [{"video": h["name"], "start": h["start"], "end": h["end"], "peak_t": h["peak"], "score": h["score"]} for h in results]
        truth = manifest["sources"][query["sequence"]]
        language.append({**query, "correct_top1": any(peak_matches(h, truth) for h in hits[:1]),
                         "correct_top5": any(peak_matches(h, truth) for h in hits[:5]), "hits": hits})
    import torch
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_sha256": file_hash(args.dataset / "manifest.json"),
            "model": MODEL_ID, "revision": REVISION, "device": encoder.device,
            "dtype": str(next(encoder.model.parameters()).dtype), "vision_tokens": encoder.vision_tokens,
            "gallery_batch_size": 4, "query_batch_size": 1,
            "gpu": torch.cuda.get_device_name() if encoder.device == "cuda" else None,
            "packages": packages,
            "model_file_sha256": {p.name: file_hash(p) for p in sorted(args.model.glob("*.safetensors"))},
            "pipeline_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): file_hash(p) for p in
                [ROOT / "desktop/backend/inference.py", ROOT / "desktop/backend/library.py", ROOT / "vsearch/text.py",
                 Path(__file__), ROOT / "scripts/retrieval_quality_metrics.py", ROOT / "scripts/prepare_retrieval_quality.py"]},
            "git_base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "frames": frames, "region_indices": region_indices, "production_image_parity_queries": parity,
            "natural_language": language, "elapsed_seconds_including_hashing": time.perf_counter() - started}
    write_json(args.output / "embedding-run.json", meta)
    library.close()


def evaluate(args, manifest):
    meta = read_json(args.output / "embedding-run.json")
    assert meta["manifest_sha256"] == file_hash(args.dataset / "manifest.json")
    embeddings = np.load(args.output / "embeddings.npz")
    protocol, frames = manifest["protocol"], meta["frames"]
    durations = {v["name"]: v["duration"] for v in manifest["videos"]}
    configurations = []
    for config in protocol["configs"]:
        indices = sample_indices(frames, config["fps"], protocol["fps"])
        sampled = [frames[i] for i in indices]
        assert len(indices) == sum(math.ceil(v["frames"] / round(protocol["fps"] / config["fps"])) for v in manifest["videos"])
        scores = np.stack([embeddings["frames"][indices] @ q for q in embeddings["queries"]])
        if config["regions"]:
            assert indices == meta["region_indices"]
            region_scores = np.einsum("qd,frd->qfr", embeddings["queries"], embeddings["regions"]).max(axis=2)
            scores = np.maximum(scores, region_scores)
        evaluated = []
        for qi, query in enumerate(manifest["queries"]):
            if query["kind"] == "object" and query["padding"] != config["padding"]:
                continue
            hits = rank(sampled, scores[qi], config["fps"], durations, protocol["max_results"])
            covered = any(peak_matches({"video": f["video"], "peak_t": f["t"]}, g) for f in sampled for g in query["gt"])
            evaluated.append({**{k: v for k, v in query.items() if k != "image"}, "sampled": covered, "hits": hits})
        summary = {}
        for kind in ("object", "scene"):
            dev = [q for q in evaluated if q["split"] == "dev" and q["kind"] == kind]
            test = [q for q in evaluated if q["split"] == "test" and q["kind"] == kind]
            fitted = calibrate(dev, protocol["negative_accept_budget_dev"])
            summary[kind] = {"dev_raw": summarize(dev), "dev_calibrated": fitted,
                             "test_raw": summarize(test), "test_calibrated": summarize(test, fitted["threshold"])}
            if kind == "object":
                for label, predicate in (("small", lambda q: q["area_fraction"] < .05),
                                         ("other", lambda q: q["area_fraction"] >= .05)):
                    summary[kind][f"test_{label}_raw"] = summarize([q for q in test if predicate(q)])
        configurations.append({**config, "sampled_frames": len(indices),
                               "indexed_vectors": len(indices) * (5 if config["regions"] else 1),
                               "summary": summary, "queries": evaluated})
        print(json.dumps({"configuration": config["id"], "test_object": summary["object"]["test_raw"]}), flush=True)
    selected = {}
    for kind in ("object", "scene"):
        best = max(configurations, key=lambda c: (c["summary"][kind]["dev_calibrated"]["correct_top1_f1"],
                                                   -c["indexed_vectors"]))
        selected[kind] = best["id"]
    report = {"schema": 1, "purpose": "Constructed labeled pilot, not product-wide accuracy",
              "protocol_sha256": manifest["protocol_sha256"], "archive_sha256": manifest["archive_sha256"],
              "protocol": protocol, "videos": manifest["videos"], "excluded_queries": manifest["excluded_queries"],
              "measurement": {"peak_match": "same video, start <= peak < end; no tolerance",
                  "temporal_match": "same video and interval IoU >= 0.5; one-to-one matching for event recall",
                  "false_accept": "absent query with at least one result above threshold",
                  "calibration": "dev only: absent FAR <= 0.05, maximize correct accepted positive top1; ties minimize wrong accepts, then maximize threshold",
                  "configuration_selection": "dev calibrated correct-top1 F1; tie prefers fewer indexed vectors",
                  "negative_budget_resolution": "18 absent dev queries per kind => 0 allowed false accepts at 5% budget",
                  "independence": "three frames per object; objects within one source share context; no independent-query confidence interval",
                  "identity_scope": "source/time retrieval against instance-presence masks, not instance identity localization within a frame",
                  "sampling": "subsample a real 2 fps desktop index on the same decoded frame lattice; coarser decoder throughput is not measured"},
              "run": {k: v for k, v in meta.items() if k not in ("frames", "region_indices")},
              "selected_on_dev": selected, "configurations": configurations}
    write_json(args.output / "report.json", report)
    compact = {**report, "configurations": [{k: v for k, v in c.items() if k != "queries"} for c in configurations]}
    write_json(args.output / "summary.json", compact)
    print(json.dumps({"selected_on_dev": selected, "report": str(args.output / "report.json")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--score-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = read_json(args.dataset / "manifest.json")
    if not args.score_only:
        build_embeddings(args, manifest)
    evaluate(args, manifest)


if __name__ == "__main__":
    main()
