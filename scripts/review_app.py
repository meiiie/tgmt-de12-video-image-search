"""Local repeatable evidence through the same HTTP API as the product."""
import argparse
import base64
import json
from pathlib import Path
import statistics
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "outputs/review-20261114"
session = json.loads((ROOT / "outputs/onboarding/panel-session.json").read_text())
params = urllib.parse.parse_qs(urllib.parse.urlsplit(session["url"]).fragment)
BASE = "http://127.0.0.1:" + params["port"][0]
HEADERS = {"Authorization": "Bearer " + params["token"][0], "Content-Type": "application/json"}

def request(path, body=None):
    raw = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=raw, headers=HEADERS)
    begin = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as response:
        result = json.load(response)
    return result, (time.perf_counter() - begin) * 1000

def search(path, mode="similar", threshold=.7, **more):
    body = {"image": base64.b64encode(path.read_bytes()).decode(), "image_mode": mode,
            "min_score": threshold, "limit": 24, **more}
    response, elapsed = request("/search", body)
    return {"response": response, "http_ms": elapsed, "query": str(path), "mode": mode, "threshold": threshold}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["import", "queries", "status"])
    args = parser.parse_args()
    if args.action == "import":
        result, _ = request("/import", {"paths": [r"D:\TaiVe\TGMT\BTL\video\bo_thu_10_video"]})
        print(result, flush=True)
    elif args.action == "status":
        result, _ = request("/library")
        print("model", result["model"], "active", result["active"], "progress", result["progress"], flush=True)
        for v in result["videos"]:
            print(v["name"][:45], v["status"], v["frames"], v.get("index_seconds"), flush=True)
        (WORK / "library-status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        queries = {
            "poster_in_library": Path(r"C:\Users\Admin\Pictures\Screenshots\Screenshot 2026-11-06 222015.png"),
            "external_cat": WORK / "external/cat.jpg",
        }
        for label, path in queries.items():
            all_runs = []
            for mode in ("similar", "detail"):
                # The first pass can load the model/cache. Five repeated passes are stored separately.
                warmup = search(path, mode)
                (WORK / f"{label}-{mode}-first.json").write_text(json.dumps(warmup, ensure_ascii=False, indent=2), encoding="utf-8")
                runs = [search(path, mode) for _ in range(5)]
                for run in runs:
                    response = run["response"]
                    assert sum(v["indexed_frames"] for v in response["per_video"]) == response["indexed_frames"]
                    assert len(response["per_video"]) == 10
                all_runs += runs
                vals = [r["http_ms"] for r in runs]
                print(label, mode, "median", round(statistics.median(vals),2),
                      "range", round(min(vals),2),round(max(vals),2), "results", len(runs[-1]["response"]["results"]), flush=True)
            (WORK / f"{label}-runs.json").write_text(json.dumps(all_runs,ensure_ascii=False,indent=2),encoding="utf-8")
