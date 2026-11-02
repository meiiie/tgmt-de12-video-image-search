"""Prepare predeclared, privately stored screenshot queries without running retrieval."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-metadata", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a fresh query directory")
    args.output.mkdir(parents=True)
    source = json.loads(args.source_metadata.read_text(encoding="utf-8"))
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(source["path"])
    queries = []
    try:
        assert cap.isOpened()
        fps = cap.get(cv2.CAP_PROP_FPS)
        for index, timestamp in enumerate(protocol["query_times"]):
            frame_index = round(timestamp * fps)
            assert cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, bgr = cap.read()
            assert ok
            actual = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            assert abs(actual - timestamp) < 1 / fps
            image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            region = protocol["gameplay_region"]
            box = (round(region["x"] * image.width), round(region["y"] * image.height),
                   round((region["x"] + region["width"]) * image.width), round((region["y"] + region["height"]) * image.height))
            for kind, query in [("full_frame", image), ("gameplay_region", image.crop(box))]:
                filename = f"query-{index:02d}-{kind}.png"
                query.save(args.output / filename)
                queries.append({"id": filename.removesuffix(".png"), "image": filename, "kind": kind,
                    "source_t": actual, "source_frame": frame_index,
                    "sha256": hashlib.sha256((args.output / filename).read_bytes()).hexdigest()})
    finally:
        cap.release()
    (args.output / "manifest.json").write_text(json.dumps({"protocol": protocol,
        "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(), "queries": queries}, indent=2), encoding="utf-8")
    print(json.dumps({"queries": len(queries), "timestamps": len(protocol["query_times"])}))


if __name__ == "__main__":
    main()
