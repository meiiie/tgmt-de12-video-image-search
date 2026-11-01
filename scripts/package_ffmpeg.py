"""Pin a current Windows FFmpeg executable and preserve its licenses/docs."""
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlretrieve
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "9.0.2"
URL = f"https://github.com/GyanD/codexffmpeg/releases/download/{VERSION}/ffmpeg-{VERSION}-essentials_build.zip"
SHA256 = "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"


def main():
    archive = ROOT / f"outputs/onboarding/ffmpeg-{VERSION}-github.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        partial = archive.with_suffix(".partial")
        urlretrieve(URL, partial)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != SHA256:
            raise SystemExit("FFmpeg download hash mismatch")
        partial.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit("FFmpeg archive hash does not match the pinned publisher checksum")
    runtime = ROOT / "desktop/runtime314"
    notices = runtime / "ffmpeg-notices"
    notices.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            name = Path(item.filename)
            if name.name == "ffmpeg.exe":
                target = runtime / "ffmpeg.exe"
            elif name.name in {"LICENSE", "README.txt"} or "doc" in name.parts:
                target = notices / Path(*name.parts[1:])
            else:
                continue
            if item.is_dir():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    (notices / "provenance.json").write_text(json.dumps({"version": VERSION, "archive": URL, "sha256": SHA256, "source": "https://github.com/FFmpeg/FFmpeg/commit/946fcce07b", "builder": "https://www.gyan.dev/ffmpeg/builds/", "license": "GPLv3"}, indent=2))
    # The desktop always uses the pinned adjacent executable, not the wheel's older copy.
    old_binary = runtime / "Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
    old_binary.unlink(missing_ok=True)
    print(f"FFmpeg {VERSION} packaged with publisher docs and license", flush=True)


if __name__ == "__main__":
    main()
