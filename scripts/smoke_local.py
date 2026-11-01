"""Run real embedding/index/query on synthetic video; this is not an accuracy benchmark."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vsearch.core import Searcher, build_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="facebook/dinov2-small")
    args = parser.parse_args()
    data = Path(__file__).resolve().parents[1] / "data"
    data.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="smoke-", dir=data))
    videos = root / "videos"
    videos.mkdir()
    query = None
    for name, color, circle in [
        ("red_square.mp4", (30, 30, 220), False),
        ("blue_circle.mp4", (220, 40, 30), True),
    ]:
        writer = cv2.VideoWriter(
            str(videos / name), cv2.VideoWriter_fourcc(*"mp4v"), 10, (224, 224)
        )
        if not writer.isOpened():
            raise RuntimeError("OpenCV could not create the smoke video")
        try:
            for i in range(20):
                frame = np.full((224, 224, 3), 245, dtype=np.uint8)
                if circle:
                    cv2.circle(frame, (112, 112), 65, color, -1)
                else:
                    cv2.rectangle(frame, (45, 45), (179, 179), color, -1)
                    cv2.line(frame, (45, 45), (179, 179), (20, 20, 20), 6)
                writer.write(frame)
                if name == "red_square.mp4" and i == 0:
                    query = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        finally:
            writer.release()

    query.save(root / "query.png")
    index = root / "index"
    stats = build_index(str(videos), str(index), model=args.model, fps=1, regions="none")
    searcher = Searcher(str(index))
    hits = searcher.search(query, mode="frame", k=2)
    if stats["frames"] != 4 or not hits or hits[0]["video"] != "red_square.mp4":
        raise AssertionError(f"Synthetic image retrieval failed: {stats}, {hits}")
    report = {
        "scope": "synthetic integration smoke; not retrieval accuracy or latency benchmark",
        "root": str(root),
        "stats": stats,
        "image_results": hits,
        "passed": True,
    }
    if searcher.emb.kind != "dino":
        text_hits = searcher.search_text("a red square", k=2, use_ordinal=False)
        if not text_hits:
            raise AssertionError("Text query returned no result on the smoke index")
        report["text_results"] = text_hits
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f'python app.py --index "{index}" --videos "{videos}"')


if __name__ == "__main__":
    main()
