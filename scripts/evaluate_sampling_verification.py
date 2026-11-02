"""Regression on the previously inspected DAVIS pilot, using real desktop search."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import cv2
from PIL import Image
from desktop.backend.inference import Encoder, MODEL_ID, REVISION
from desktop.backend.library import Library
from desktop.backend.store import Store
from retrieval_quality_metrics import peak_matches, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a fresh output directory")
    args.output.mkdir(parents=True)
    cv2.setNumThreads(2)
    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    queries = [q for q in manifest["queries"] if q["kind"] == "scene" or q["padding"] == .4]
    encoder = Encoder(args.output, str(args.model.resolve()), 140)
    configurations = []
    for mode, fps in [("uniform", .1), ("hybrid", .1), ("uniform", 1.0)]:
        name = f"{mode}_{fps}fps"
        directory = args.output / name
        Store(directory).update_settings({"fps": fps, "sampling": mode, "model_path": str(args.model.resolve()), "batch_size": 4})
        library = Library(directory, encoder, start_worker=False)
        library.import_paths([str((args.dataset / "videos" / v["name"]).resolve()) for v in manifest["videos"]])
        for video in library.store.videos():
            library.index_video(video)
            final = library.store.video(video["id"])
            assert final["status"] == "ready", final["error"]
        with library.store.connect() as db:
            frames = [dict(r) for r in db.execute("SELECT v.name AS video,f.t FROM frames f JOIN videos v ON v.id=f.video_id")]
        evaluated = []
        for i, query in enumerate(queries):
            with Image.open(args.dataset / query["image"]) as image:
                image = image.convert("RGB")
                for image_mode in ("similar", "detail"):
                    result = library.search(image=image, image_mode=image_mode, limit=10)
                    hits = [{"video": r["name"], "start": r["start"], "end": r["end"], "peak_t": r["peak"], "score": r["score"],
                             **({"verification": r["verification"]} if "verification" in r else {})} for r in result["results"]]
                    evaluated.append({**{k: v for k, v in query.items() if k != "image"}, "image_mode": image_mode,
                        "sampled": any(peak_matches({"video": f["video"], "peak_t": f["t"]}, g) for f in frames for g in query["gt"]),
                        "hits": hits, "verification": result.get("verification")})
            if i % 20 == 0:
                print(json.dumps({"configuration": name, "query": i + 1, "total": len(queries)}), flush=True)
        summary = {}
        for image_mode in ("similar", "detail"):
            summary[image_mode] = {kind: {split: summarize([q for q in evaluated if q["image_mode"] == image_mode and q["kind"] == kind and q["split"] == split])
                                         for split in ("dev", "test")} for kind in ("object", "scene")}
        language = []
        for query in manifest["protocol"]["natural_language_checks"]:
            result = library.search(text=query["text"], limit=5)["results"]
            truth = manifest["sources"][query["sequence"]]
            language.append({**query, "correct_top1": any(peak_matches({"video": h["name"], "peak_t": h["peak"]}, truth) for h in result[:1])})
        configuration = {"id": name, "frames": len(frames), "summary": summary, "language": language, "queries": evaluated}
        configurations.append(configuration)
        (args.output / f"{name}.json").write_text(json.dumps(configuration, ensure_ascii=False, indent=2), encoding="utf-8")
        library.close()
        print(json.dumps({"completed": name, "test_object": summary["detail"]["object"]["test"]}), flush=True)
    report = {"scope": "Regression: previous pilot results already inspected; not a new blind test",
              "created_utc": datetime.now(timezone.utc).isoformat(), "model": MODEL_ID, "revision": REVISION,
              "dtype": str(next(encoder.model.parameters()).dtype), "query_padding": .4,
              "selection": "All scene queries and all pad40 object queries. Fixed verification rules; no threshold tuning on test.",
              "detail_intervals": "2-second viewing windows clipped at detected shots; not predicted full occurrences",
              "code_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [
                  "desktop/backend/sampling.py", "desktop/backend/verification.py", "desktop/backend/moments.py", "desktop/backend/library.py"]},
              "configurations": configurations}
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["configurations"] = [{k: v for k, v in c.items() if k != "queries"} for c in configurations]
    (args.output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
