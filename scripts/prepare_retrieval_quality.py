"""Build the declared image-retrieval pilot from a local official DAVIS archive."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import zipfile

import cv2
import numpy as np
from PIL import Image


def intervals(flags, offset, fps):
    result, start = [], None
    for i, present in enumerate([*flags, False]):
        if present and start is None:
            start = i
        if not present and start is not None:
            result.append({"start": offset + start / fps, "end": offset + i / fps})
            start = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.protocol.read_bytes()
    protocol = json.loads(raw)
    output = args.output
    for sub in ("videos", "queries", "provenance"):
        (output / sub).mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise SystemExit("Use a new output folder to preserve a prepared benchmark")
    holdout, fps = protocol["holdout_frames"], protocol["fps"]
    assert max(protocol["query_frames"]) < holdout
    sources = {s["sequence"]: s for s in protocol["sources"]}
    included = [s for group in protocol["gallery_groups"] for s in group]
    assert len(included) == len(set(included))
    assert set(included) == {s for s, spec in sources.items() if spec["present"]}
    manifest = {"protocol_sha256": hashlib.sha256(raw).hexdigest(), "protocol": protocol,
                "videos": [], "sources": {}, "queries": [], "excluded_queries": []}
    archive_hash = hashlib.sha256()
    with args.archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            archive_hash.update(chunk)
    manifest["archive_sha256"] = archive_hash.hexdigest()
    with zipfile.ZipFile(args.archive) as archive:
        for name in ("README.md", "SOURCES.md"):
            (output / "provenance" / name).write_bytes(archive.read("DAVIS/" + name))
        names = archive.namelist()
        def image(seq, frame):
            return Image.open(BytesIO(archive.read(f"DAVIS/JPEGImages/480p/{seq}/{frame:05d}.jpg"))).convert("RGB")
        def mask(seq, frame):
            return np.array(Image.open(BytesIO(archive.read(f"DAVIS/Annotations/480p/{seq}/{frame:05d}.png"))))
        for vi, group in enumerate(protocol["gallery_groups"]):
            filename = f"gallery-{vi:02d}.mp4"
            writer = cv2.VideoWriter(str(output / "videos" / filename), cv2.VideoWriter_fourcc(*"mp4v"), fps, (854, 480))
            assert writer.isOpened()
            offset = 0
            try:
                for seq in group:
                    frames = sorted(n for n in names if n.startswith(f"DAVIS/JPEGImages/480p/{seq}/") and n.endswith(".jpg"))
                    kept = list(range(holdout, len(frames)))
                    assert kept
                    masks = [mask(seq, frame) for frame in kept]
                    objects = {str(oid): [{"video": filename, **span} for span in intervals(
                        [np.count_nonzero(m == oid) >= protocol["min_mask_pixels"] for m in masks], offset / fps, fps)]
                        for oid in sources[seq]["objects"]}
                    manifest["sources"][seq] = {"video": filename, "start": offset / fps, "end": (offset + len(kept)) / fps,
                                                 "objects": objects, "source_frames": [holdout, len(frames) - 1]}
                    for frame in kept:
                        rgb = np.asarray(image(seq, frame))
                        assert rgb.shape[:2] == (480, 854), (seq, rgb.shape)
                        writer.write(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                    offset += len(kept)
            finally:
                writer.release()
            manifest["videos"].append({"name": filename, "frames": offset, "duration": offset / fps})
        for seq, spec in sources.items():
            truth = manifest["sources"].get(seq)
            for frame in protocol["query_frames"]:
                rgb, labels = image(seq, frame), mask(seq, frame)
                scene_id = f"{seq}-scene-{frame}"
                path = f"queries/{scene_id}.png"
                rgb.save(output / path)
                manifest["queries"].append({"id": scene_id, "target": f"{seq}-scene", "sequence": seq,
                    "split": spec["split"], "present": spec["present"], "kind": "scene", "padding": None,
                    "image": path, "gt": [{k: truth[k] for k in ("video", "start", "end")}] if truth else []})
                for oid in spec["objects"]:
                    ys, xs = np.where(labels == oid)
                    if len(xs) < protocol["min_mask_pixels"]:
                        manifest["excluded_queries"].append({"sequence": seq, "frame": frame, "object": oid, "reason": "mask too small or absent"})
                        continue
                    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
                    for pad in protocol["query_padding"]:
                        dx, dy = round((x1 - x0) * pad), round((y1 - y0) * pad)
                        box = (max(0, x0 - dx), max(0, y0 - dy), min(rgb.width, x1 + dx), min(rgb.height, y1 + dy))
                        identity = f"{seq}-object{oid}-{frame}-pad{round(pad * 100)}"
                        path = f"queries/{identity}.png"
                        rgb.crop(box).save(output / path)
                        gt = truth["objects"][str(oid)] if truth else []
                        assert not spec["present"] or gt, identity
                        manifest["queries"].append({"id": identity, "target": f"{seq}-object{oid}", "sequence": seq,
                            "split": spec["split"], "present": spec["present"], "kind": "object", "padding": pad,
                            "area_fraction": len(xs) / (rgb.width * rgb.height), "image": path, "gt": gt})
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"videos": len(manifest["videos"]), "seconds": sum(v["duration"] for v in manifest["videos"]),
                      "queries_including_variants": len(manifest["queries"]), "excluded": manifest["excluded_queries"]}), flush=True)


if __name__ == "__main__":
    main()
