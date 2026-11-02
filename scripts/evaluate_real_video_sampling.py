"""Known-timestamp recovery and foreign-reference probes on a ready local video library."""
import argparse
import base64
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
from desktop.backend.inference import Encoder, MODEL_ID, REVISION
from vsearch.text import text_search


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--davis", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a fresh output directory")
    session = json.loads(args.session.read_text(encoding="utf-8"))
    params = parse_qs(urlsplit(session["url"]).fragment)
    origin = "http://127.0.0.1:" + params["port"][0]
    def request(path, body=None, method=None):
        headers = {"Authorization": "Bearer " + params["token"][0]}
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(origin + path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method=method)
        with urlopen(req, timeout=300) as response:
            return json.load(response)
    state = request("/library")
    if len(state["videos"]) != 1 or state["videos"][0]["status"] != "ready":
        raise SystemExit("Evaluation requires a completely indexed, single-video library")
    args.output.mkdir(parents=True)
    manifest = json.loads((args.queries / "manifest.json").read_text(encoding="utf-8"))
    protocol = manifest["protocol"]
    library_root = Path(session["data_dir"])
    db = sqlite3.connect((library_root / "library.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        records = db.execute("SELECT f.*,v.name,v.duration FROM frames f JOIN videos v ON v.id=f.video_id ORDER BY t").fetchall()
    finally:
        db.close()
    matrix = np.stack([np.frombuffer(r["embedding"], dtype=np.float32) for r in records])
    times = np.array([r["t"] for r in records])
    shots = {(r["shot_start"], r["shot_end"]) for r in records}
    sampling_coverage = {}
    for fps in (.1, .5):
        indices = np.flatnonzero(np.round(times * protocol["fps"]).astype(int) % round(protocol["fps"] / fps) == 0)
        represented = {(records[i]["shot_start"], records[i]["shot_end"]) for i in indices}
        sampling_coverage[f"uniform_{fps}fps"] = {"frames": len(indices), "detected_shots_with_sample": len(represented),
                                                "detected_shots_without_sample": len(shots - represented)}
    sampling_coverage["hybrid_0.5fps"] = {"frames": len(records), "detected_shots_with_sample": len(shots),
                                        "detected_shots_without_sample": 0}
    queries = [{**q, "category": "known_source", "file": args.queries / q["image"],
                "held_out": not np.any(np.abs(times - q["source_t"]) < .5 / protocol["fps"])} for q in manifest["queries"]]
    references = json.loads((args.davis / "manifest.json").read_text(encoding="utf-8"))["queries"]
    for identity in protocol["foreign_reference_ids"]:
        q = next(q for q in references if q["id"] == identity)
        queries.append({"id": identity, "category": "foreign_reference", "kind": "foreign", "file": args.davis / q["image"]})
    encoder = Encoder(args.output, str(args.model.resolve()), 140)
    query_vectors = []
    for q in queries:
        with Image.open(q["file"]) as image:
            query_vectors.append(encoder.query(image=image.convert("RGB")))
    dtype = str(next(encoder.model.parameters()).dtype)
    encoder.model = None
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    evaluated = []
    for qi, query in enumerate(queries):
        results = {}
        coverage = None
        if query["category"] == "known_source":
            order = np.argsort(-(matrix @ query_vectors[qi]), kind="stable")
            near = np.abs(times - query["source_t"]) <= protocol["known_source_tolerance_seconds"]
            ranks = np.flatnonzero(near[order])
            coverage = {"nearest_indexed_frame_seconds": float(np.min(np.abs(times - query["source_t"]))),
                        "source_frames_in_tolerance": int(near.sum()),
                        "best_raw_frame_rank": int(ranks[0] + 1) if len(ranks) else None,
                        "source_within_first_48_candidates": bool(len(ranks) and ranks[0] < 48)}
        for fps in (.1, .5):
            indices = np.flatnonzero(np.round(times * protocol["fps"]).astype(int) % round(protocol["fps"] / fps) == 0)
            meta = [{"video": "user-video", "t": records[i]["t"], "kind": "frame"} for i in indices]
            hits = text_search(meta, None, None, fps, scores=matrix[indices] @ query_vectors[qi], w=1, k=10)
            for hit in hits:
                hit["end"] = min(hit["end"], state["videos"][0]["duration"])
                hit["frame_id"] = records[int(np.argmin(np.abs(times - hit["peak_t"])))]["id"]
            results[f"uniform_{fps}fps"] = {"hits": hits, "indexed_frames": len(indices)}
        payload = base64.b64encode(query["file"].read_bytes()).decode()
        for mode in ("similar", "detail"):
            response = request("/search", {"image": payload, "image_mode": mode, "limit": 10})
            hits = [{"video": "user-video", "start": h["start"], "end": h["end"], "peak_t": h["peak"],
                     "frame_id": h["frame_id"], "score": h["score"],
                     **({"verification": h["verification"]} if "verification" in h else {})} for h in response["results"]]
            results["hybrid_" + mode] = {"hits": hits, "indexed_frames": response["indexed_frames"],
                                        "verification": response.get("verification"),
                                        "elapsed_ms": response["elapsed_ms"]}
        evaluated.append({**{k: v for k, v in query.items() if k not in ("file", "image")},
                          "candidate_coverage": coverage, "results": results})
        (args.output / "queries-partial.json").write_text(json.dumps(evaluated, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"query": qi + 1, "total": len(queries), "id": query["id"],
                          "detail_results": len(results["hybrid_detail"]["hits"])}), flush=True)
    summary = {}
    for config in evaluated[0]["results"]:
        kinds = {}
        for kind in ("full_frame", "gameplay_region"):
            group = [q for q in evaluated if q["category"] == "known_source" and q["kind"] == kind and q["held_out"]]
            kinds[kind] = {"queries": len(group), "returned_queries": sum(bool(q["results"][config]["hits"]) for q in group),
                "known_source_top1": sum(any(abs(h["peak_t"] - q["source_t"]) <= protocol["known_source_tolerance_seconds"] for h in q["results"][config]["hits"][:1]) for q in group),
                "known_source_top5": sum(any(abs(h["peak_t"] - q["source_t"]) <= protocol["known_source_tolerance_seconds"] for h in q["results"][config]["hits"][:5]) for q in group)}
        kinds["foreign_reference_returned"] = sum(bool(q["results"][config]["hits"]) for q in evaluated if q["category"] == "foreign_reference")
        kinds["foreign_reference_queries"] = len(protocol["foreign_reference_ids"])
        summary[config] = kinds
    language = []
    for text in ("màn hình bỏ phiếu cho người chơi", "nhân vật hoạt hình trong căn phòng có đèn xanh", "logo trên nền đen"):
        response = request("/search", {"text": text, "limit": 3})
        language.append({"text": text, "hits": [{"peak_t": h["peak"], "frame_id": h["frame_id"], "score": h["score"]} for h in response["results"]]})
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "protocol": protocol,
        "protocol_sha256": manifest["protocol_sha256"], "model": MODEL_ID, "revision": REVISION, "query_dtype": dtype,
        "backend_device": state["model"]["device"], "source_seconds": state["videos"][0]["duration"],
        "indexed_frames": len(records), "shot_count": len({r["shot_start"] for r in records}),
        "sampling_coverage": sampling_coverage,
        "settings": {k: state["settings"][k] for k in ("fps", "sampling", "vision_tokens", "batch_size")},
        "baseline": "Uniform baselines are anchor subsets of the same newly encoded index; no live library mutation",
        "exact_indexed_queries_excluded": [q["id"] for q in evaluated if q["category"] == "known_source" and not q["held_out"]],
        "summary": summary, "language": language, "queries": evaluated,
        "code_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ["desktop/backend/library.py", "desktop/backend/sampling.py", "desktop/backend/verification.py", "desktop/backend/moments.py"]}}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "exact_indexed_queries_excluded": report["exact_indexed_queries_excluded"]}), flush=True)


if __name__ == "__main__":
    main()
