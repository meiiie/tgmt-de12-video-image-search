"""Start the current backend on a separate copy of a local library, without native UI."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desktop.backend.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-library", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18767)
    args = parser.parse_args()
    if args.source_library.resolve() == args.data_dir.resolve() or (args.data_dir / "library.sqlite3").exists():
        raise SystemExit("Target must be a separate library with no existing database")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect((args.source_library / "library.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    target = sqlite3.connect(args.data_dir / "library.sqlite3")
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    Store(args.data_dir).update_settings({"fps": .5, "sampling": "hybrid", "batch_size": 4,
        "model_path": str(args.model.resolve()), "paused": False})
    token = secrets.token_hex(32)
    env = dict(os.environ, FRAMEATLAS_TOKEN=token, HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
               TOKENIZERS_PARALLELISM="false", PYTHONUTF8="1")
    args.session.parent.mkdir(parents=True, exist_ok=True)
    command = [str(args.runtime.resolve()), "-u", "-c",
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('desktop.backend.server',run_name='__main__')",
        str(ROOT), "--data-dir", str(args.data_dir.resolve()), "--port", str(args.port)]
    with (args.session.parent / "quality-backend.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name == "nt" else 0)
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Backend stopped; inspect quality-backend.log")
            try:
                request = Request(f"http://127.0.0.1:{args.port}/health", headers={"Authorization": "Bearer " + token})
                with urlopen(request, timeout=2):
                    break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("Backend did not become ready")
        session = {"backend": process.pid, "url": f"http://127.0.0.1:1420/#port={args.port}&token={token}",
                   "data_dir": str(args.data_dir.resolve()), "runtime": str(args.runtime.resolve())}
        args.session.write_text(json.dumps(session), encoding="utf-8")
        print(json.dumps({"ready": True, "port": args.port, "session_saved": True}), flush=True)
    except BaseException:
        process.terminate()
        process.wait()
        raise


if __name__ == "__main__":
    main()
