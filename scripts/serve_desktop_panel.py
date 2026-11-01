"""Start the real library in a browser panel, without native windows or input."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/onboarding"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(32)
    env = dict(os.environ, FRAMEATLAS_TOKEN=token,
               HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    processes = []
    try:
        for name, command, cwd in [
            ("backend", [str(ROOT / "desktop/runtime314/python.exe"), "-u", "-c",
                         "import sys, runpy; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module('desktop.backend.server', run_name='__main__')",
                         str(ROOT), "--data-dir",
                         str(ROOT / "data/desktop-acceptance"), "--port", "18766"], ROOT),
            ("frontend", [shutil.which("node"), "node_modules/vite/bin/vite.js", "preview",
                          "--host", "127.0.0.1", "--port", "1420", "--strictPort"], ROOT / "desktop"),
        ]:
            with (OUTPUT / f"panel-{name}.log").open("w") as log:
                processes.append(subprocess.Popen(command, cwd=cwd, env=env,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW))
        for attempt in range(60):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("Panel service stopped; see panel logs")
            try:
                with urlopen(Request("http://127.0.0.1:18766/health",
                                     headers={"Authorization": f"Bearer {token}"}), timeout=2):
                    pass
                with urlopen("http://127.0.0.1:1420", timeout=2):
                    pass
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("Panel services did not become ready")
        session = dict(backend=processes[0].pid, frontend=processes[1].pid,
                       url=f"http://127.0.0.1:1420/#port=18766&token={token}")
        (OUTPUT / "panel-session.json").write_text(json.dumps(session), encoding="utf-8")
        print("FrameAtlas ready on port 1420; connection saved in ignored panel-session.json")
    except BaseException:
        for process in processes:
            process.terminate()
        raise


if __name__ == "__main__":
    main()
