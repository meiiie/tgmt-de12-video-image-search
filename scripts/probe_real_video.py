"""Inspect supplied video and compare sparse sampling against decoding every frame."""
import argparse
import json
from pathlib import Path
import time

import cv2
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/real-video"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    samples = []
    canvas = Image.new("RGB", (1280, 4 * 204), "#f4f3ec")
    draw = ImageDraw.Draw(canvas)
    for i in range(16):
        requested = round((duration - 1) * i / 15, 2)
        cap.set(cv2.CAP_PROP_POS_MSEC, requested * 1000)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot decode frame at {requested}")
        actual = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.save(args.output / f"sample-{i:02}.jpg", quality=90)
        image.thumbnail((320, 180))
        x, y = i % 4 * 320, i // 4 * 204
        canvas.paste(image, (x, y))
        draw.text((x + 6, y + 183), f"{i:02}  {int(actual)//3600:02}:{int(actual)//60%60:02}:{actual%60:05.2f}", fill="#202820")
        samples.append({"sample": i, "requested": requested, "actual": actual})
    cap.release()
    canvas.save(args.output / "contact-sheet.jpg", quality=90)
    measurements = []
    for method in ("sequential", "seek"):
        cap = cv2.VideoCapture(str(args.source))
        started = time.perf_counter()
        timestamps = []
        step = round(fps * 10)
        for index in range(12):
            if method == "seek":
                cap.set(cv2.CAP_PROP_POS_FRAMES, index * step)
            ok, frame = cap.read()
            assert ok
            timestamps.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
            if method == "sequential" and index < 11:
                for _ in range(step - 1):
                    assert cap.grab()
        elapsed = time.perf_counter() - started
        cap.release()
        measurements.append({"method": method, "seconds": elapsed, "timestamps": timestamps})
        print(json.dumps(measurements[-1]), flush=True)
    report = {"source": str(args.source), "duration": duration, "fps": fps, "samples": samples, "sampling": measurements}
    (args.output / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
