"""Exercise the shipped engine/runtime over HTTP without opening a desktop window."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/onboarding"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, default=ROOT / "desktop/src-tauri/target/release")
    parser.add_argument("--report", type=Path, default=OUT / "desktop-package-verification.json")
    args = parser.parse_args()
    build = args.build_dir.resolve()
    engine = build / "engine"
    for source in [* (ROOT / "desktop/backend").glob("*.py"), * (ROOT / "vsearch").glob("*.py")]:
        packaged = engine / source.relative_to(ROOT)
        assert packaged.read_bytes() == source.read_bytes(), f"Stale packaged source: {packaged}"
    assert (build / "runtime/ffmpeg.exe").is_file()
    data = ROOT / "data/desktop-offline-acceptance"
    assert (data / "library.sqlite3").is_file(), "Run offline acceptance first"
    token = secrets.token_hex(32)
    env = dict(os.environ, FRAMEATLAS_TOKEN=token, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
               HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    bootstrap = "import sys, runpy; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('desktop.backend.server', run_name='__main__')"
    with (OUT / "packaged-worker.log").open("w") as log:
        worker = subprocess.Popen([str(build / "runtime/python.exe"), "-u", "-c", bootstrap,
            str(engine), "--data-dir", str(data), "--parent", str(os.getpid())], cwd=build, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            ready = json.loads(worker.stdout.readline())
            base = f"http://127.0.0.1:{ready['port']}"
            def request(path, body=None, headers=None):
                supplied = {"Authorization": f"Bearer {token}", **(headers or {})}
                if body is not None:
                    supplied["Content-Type"] = "application/json"
                req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=supplied)
                return urlopen(req, timeout=180)
            for _ in range(60):
                try:
                    with request("/health") as response:
                        assert json.load(response)["ok"]
                    break
                except OSError:
                    time.sleep(.5)
            else:
                raise AssertionError("Packaged worker not healthy")
            try:
                urlopen(base + "/library", timeout=2)
                raise AssertionError("Unauthenticated request succeeded")
            except HTTPError as error:
                assert error.code == 401
            with request("/search", {"text": "con ong trên bông hoa"}) as response:
                search = json.load(response)
            first = search["results"][0]
            assert first["name"] == "flower.mp4"
            encoded = base64.b64encode((OUT / "flower-query.png").read_bytes()).decode()
            with request("/search", {"image": encoded}) as response:
                assert json.load(response)["results"][0]["name"] == "flower.mp4"
            with request(f"/media/{first['video_id']}", headers={"Range": "bytes=0-99"}) as response:
                assert response.status == 206 and len(response.read()) == 100
            output = OUT / f"packaged-export-{int(time.time())}.mp4"
            with request("/export", {"video_id": first["video_id"], "start": 1, "end": 3, "path": str(output)}) as response:
                assert Path(json.load(response)["path"]).stat().st_size > 1000
            verify_media = "import cv2, sys; c=cv2.VideoCapture(sys.argv[1]); assert c.read()[0]; d=c.get(cv2.CAP_PROP_FRAME_COUNT)/c.get(cv2.CAP_PROP_FPS); c.release(); assert abs(d-2)<.1; print(d)"
            duration = float(subprocess.check_output([str(build / "runtime/python.exe"), "-c", verify_media, str(output)], text=True, creationflags=subprocess.CREATE_NO_WINDOW))
            files = [build / "frameatlas.exe", * (build / "bundle/nsis").glob("*-setup.exe")]
            report = {"passed": True, "packaged_source_matches": True, "offline": True,
                "text_and_image_first": first["name"], "cold_search_ms": search["elapsed_ms"],
                "range_status": 206, "unauthorized_status": 401, "export_duration": duration,
                "artifacts": [{"path": str(path), "bytes": path.stat().st_size,
                    "sha256": hashlib.file_digest(path.open("rb"), "sha256").hexdigest()} for path in files]}
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print("Packaged runtime, source, EG2 text/image, media range and clip export: PASSED")
        finally:
            worker.terminate()
            worker.wait(timeout=15)


if __name__ == "__main__":
    main()
