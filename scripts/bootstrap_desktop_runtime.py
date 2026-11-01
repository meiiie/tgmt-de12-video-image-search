"""Build an isolated, current Windows runtime without installing system Python."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
from urllib.request import urlretrieve
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "desktop/runtime314"
VERSION = "3.14.10"
SHA256 = "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159"
URL = f"https://www.python.org/ftp/python/{VERSION}/python-{VERSION}-embed-amd64.zip"


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "outputs/onboarding" / f"python-{VERSION}-embed-amd64.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        urlretrieve(URL, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit(f"Official Python SHA256 mismatch: {digest}")
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(RUNTIME)
    (RUNTIME / "python314._pth").write_text("python314.zip\n.\nLib/site-packages\nimport site\n", encoding="utf-8")
    site = RUNTIME / "Lib/site-packages"
    site.mkdir(parents=True, exist_ok=True)
    pip = metadata.distribution("pip")
    for file in pip.files:
        if ".." in file.parts or "__pycache__" in file.parts:
            continue
        source = Path(pip.locate_file(file))
        target = site / file
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    python = str(RUNTIME / "python.exe")
    lock_path = ROOT / "desktop/runtime-requirements.lock"
    pins = lock_path.read_text(encoding="utf-8").splitlines()
    torch_pins = [pin for pin in pins if pin.startswith(("torch==", "torchvision=="))]
    other_pins = [pin for pin in pins if pin and pin not in torch_pins]
    subprocess.run([python, "-m", "pip", "install", "--no-compile", "--no-deps", "--index-url", "https://download.pytorch.org/whl/cpu", *torch_pins], check=True)
    subprocess.run([python, "-m", "pip", "install", "--no-compile", "--no-deps", *other_pins], check=True)
    subprocess.run([python, "-m", "pip", "check"], check=True)
    lock = subprocess.check_output([python, "-m", "pip", "freeze"], text=True)
    (RUNTIME / "DEPENDENCIES.txt").write_text(lock, encoding="utf-8")
    report = {"python": VERSION, "url": URL, "archive_sha256": digest}
    (RUNTIME / "runtime-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)
    from package_ffmpeg import main as package_ffmpeg
    package_ffmpeg()


if __name__ == "__main__":
    main()
