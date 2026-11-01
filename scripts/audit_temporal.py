"""Check temporal retrieval invariants without downloading models or datasets."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vsearch.text import text_search


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    checks = []

    meta = [
        {"video": f"{i}.mp4", "t": 0.0, "kind": "frame"}
        for i in range(7)
    ]
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.99])
    ranked = text_search(meta, None, None, 1, w=1, k=1, scores=scores)
    reversed_ranked = text_search(
        meta[::-1], None, None, 1, w=1, k=1, scores=scores[::-1]
    )
    checks.append({
        "name": "global_best_is_independent_of_video_order",
        "passed": bool(ranked and reversed_ranked
                       and ranked[0]["video"] == reversed_ranked[0]["video"] == "6.mp4"),
        "expected": "6.mp4 in both orders",
        "actual": {"forward": ranked, "reversed": reversed_ranked},
    })

    meta = [{"video": "one.mp4", "t": float(i), "kind": "frame"} for i in range(5)]
    ranked = text_search(
        meta, None, None, 1, w=1, k=3,
        scores=np.array([0.9, 0.8, 0.0, 0.7, 0.0]),
    )
    checks.append({
        "name": "disconnected_second_event_is_returned",
        "passed": any(segment["peak_t"] == 3.0 for segment in ranked),
        "expected": "a separate event with peak_t=3.0",
        "actual": ranked,
    })

    try:
        ranked = text_search(
            [{"video": "one.mp4", "t": 0.0, "kind": "frame"}],
            None, None, 1, ordinal=1, scores=np.array([0.9]),
            ord_v2={"rho": 0.3, "gap": 1.0, "dup": None},
        )
        checks.append({
            "name": "ordinal_single_frame_does_not_crash",
            "passed": isinstance(ranked, list),
            "expected": "a result list, which may be empty",
            "actual": ranked,
        })
    except IndexError as error:
        checks.append({
            "name": "ordinal_single_frame_does_not_crash",
            "passed": False,
            "expected": "a result list, which may be empty",
            "actual": f"{type(error).__name__}: {error}",
        })

    report = {"passed": all(check["passed"] for check in checks), "checks": checks}
    serialized = json.dumps(report, indent=2)
    print(serialized)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
