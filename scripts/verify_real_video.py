"""Measure a running local library against user-supplied visual queries.

Results and source images stay under the chosen local output directory. This is
an integration probe, not an accuracy benchmark: inspect the retrieved thumbnails.
"""
import argparse
import base64
import json
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--video-id")
    parser.add_argument("--wait", type=float, default=0)
    args = parser.parse_args()
    session = json.loads(args.session.read_text(encoding="utf-8"))
    params = parse_qs(urlsplit(session["url"]).fragment)
    base = "http://127.0.0.1:" + params["port"][0]
    headers = {"Authorization": "Bearer " + params["token"][0]}
    args.output.mkdir(parents=True, exist_ok=True)

    def request(path, body=None, extra=None):
        return urlopen(Request(base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={**headers, "Content-Type": "application/json", **(extra or {})}), timeout=300)

    def api(path, body=None):
        with request(path, body) as response:
            return json.load(response)

    started = time.monotonic()
    samples = []
    while True:
        try:
            library = api("/library")
        except OSError:
            if time.monotonic() - started >= args.wait:
                raise
            time.sleep(3)
            continue
        videos = [v for v in library["videos"] if not args.video_id or v["id"] == args.video_id]
        if len(videos) != 1:
            raise ValueError("Select exactly one video with --video-id")
        video = videos[0]
        sample = {"elapsed": round(time.monotonic() - started, 2), "frames": video["frames"], "status": video["status"], "progress": library.get("progress")}
        if not samples or sample["elapsed"] - samples[-1]["elapsed"] >= 60 or video["status"] == "ready":
            samples.append(sample)
            print(json.dumps(sample), flush=True)
            (args.output / "index-progress.json").write_text(json.dumps(samples, indent=2))
        if video["status"] == "ready":
            break
        if video["status"] in {"error", "cancelled"}:
            raise RuntimeError(video["error"] or video["status"])
        if time.monotonic() - started >= args.wait:
            raise TimeoutError("Video is not fully indexed yet")
        time.sleep(3)

    source = Path(video["path"])
    original = source.stat()
    report = {"video": {key: video[key] for key in ("id", "duration", "width", "height", "frames", "total")}, "settings": {k: library["settings"][k] for k in ("fps", "batch_size", "vision_tokens")}, "device": library["model"]["device"], "queries": []}
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    for case in cases:
        body = {"video_id": video["id"], "limit": 5}
        if "image" in case:
            body["image"] = base64.b64encode(Path(case["image"]).read_bytes()).decode()
        else:
            body["text"] = case["text"]
        for key in ("start", "end", "occurrence"):
            if key in case:
                body[key] = case[key]
        t = time.perf_counter()
        result = api("/search", body)
        measurement = {"case": case, "wall_ms": round((time.perf_counter() - t) * 1000), **result}
        if "start" in body or "end" in body:
            assert all(body.get("start", 0) <= r["start"] <= r["peak"] < r["end"] <= body.get("end", video["duration"]) for r in result["results"])
        for rank, item in enumerate(result["results"]):
            with request(f'/thumbnails/{item["frame_id"]}') as response:
                (args.output / f'{case["id"]}-{rank + 1}.jpg').write_bytes(response.read())
            item.pop("path", None)
            item.pop("name", None)
        report["queries"].append(measurement)
        print(json.dumps({"case": case["id"], "wall_ms": measurement["wall_ms"], "peaks": [r["peak"] for r in result["results"]]}), flush=True)
        (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with request(f'/media/{video["id"]}', extra={"Range": f"bytes={original.st_size - 100}-{original.st_size - 1}"}) as response:
        assert response.status == 206 and len(response.read()) == 100
        report["tail_range"] = response.headers["Content-Range"]
    final = source.stat()
    assert (original.st_size, original.st_mtime_ns) == (final.st_size, final.st_mtime_ns)
    report["source_unchanged"] = True
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
