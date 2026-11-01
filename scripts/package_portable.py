"""Create a portable Windows bundle without Python bytecode or C++ build headers."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "desktop/src-tauri/target/release"
OUTPUT = ROOT / "outputs/releases"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / "FrameAtlas_0.1.0_windows-x64-portable.zip"
    files = [BUILD / "frameatlas.exe", BUILD / "THIRD_PARTY.md"]
    for folder in ("runtime", "engine"):
        for path in (BUILD / folder).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(BUILD)
            if relative.is_relative_to("runtime/Lib/site-packages/torch/include"):
                continue
            files.append(path)
    partial = target.with_suffix(".partial.zip")
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for index, path in enumerate(files):
            bundle.write(path, Path("FrameAtlas") / path.relative_to(BUILD))
            if index % 2000 == 0:
                print(f"Archived {index}/{len(files)} files", flush=True)
    with zipfile.ZipFile(partial) as bundle:
        assert bundle.testzip() is None, "Portable archive CRC check failed"
    partial.replace(target)
    with target.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"path": str(target), "files": len(files), "bytes": target.stat().st_size, "sha256": digest, "crc_verified": True}
    (OUTPUT / "portable-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
