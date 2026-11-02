"""Publish numeric evidence without copying private query images, media paths or tokens."""
import argparse
import csv
import json
from pathlib import Path

from retrieval_quality_metrics import peak_matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regression", type=Path, required=True)
    parser.add_argument("--real", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    regression = json.loads(args.regression.read_text(encoding="utf-8"))
    real = json.loads(args.real.read_text(encoding="utf-8"))
    # The evaluators deliberately exclude original paths. Refuse unexpected private fields.
    def check(value):
        if isinstance(value, dict):
            forbidden = {"token", "path", "file", "data_dir", "model_path", "image"} & value.keys()
            if forbidden:
                raise ValueError(f"Unexpected private fields: {sorted(forbidden)}")
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(regression)
    check(real)
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for configuration in regression["configurations"]:
        for query in configuration.pop("queries"):
            hits = query["hits"]
            audit = query.get("verification") or {}
            rows.append({"configuration": configuration["id"], "image_mode": query["image_mode"],
                "query_id": query["id"], "split": query["split"], "kind": query["kind"],
                "present": bool(query["gt"]), "sampled": query["sampled"], "returned": bool(hits),
                "correct_top1": any(peak_matches(h, g) for h in hits[:1] for g in query["gt"]),
                "correct_top5": any(peak_matches(h, g) for h in hits[:5] for g in query["gt"]),
                "checked": audit.get("checked", ""), "matched": audit.get("matched", ""),
                "unavailable": audit.get("unavailable", ""),
                "ground_truth_json": json.dumps(query["gt"], separators=(",", ":")),
                "hits_json": json.dumps(hits, separators=(",", ":"))})
    with (args.output / "sampling-verification-20261102-queries.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for name, report in (("sampling-verification-20261102.json", regression), ("real-video-sampling-20261102.json", real)):
        (args.output / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"regression_query_runs": len(rows), "real_queries": len(real["queries"])}))


if __name__ == "__main__":
    main()
