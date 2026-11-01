"""Assemble a separate portable CUDA runtime after validating its wheels locally."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, default=ROOT / "desktop/src-tauri/target/release")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a fresh output directory to avoid mixing runtime versions")
    assert (args.site / "torch").is_dir() and (args.site / "torchvision").is_dir()
    args.output.mkdir(parents=True)

    def ignored(parent, names):
        result = [name for name in names if name == "__pycache__"]
        if Path(parent).name == "site-packages":
            result += [name for name in names if name in {"torch", "torchgen", "functorch"} or name.startswith(("torch-", "torchvision"))]
        return result

    for name in ("frameatlas.exe", "THIRD_PARTY.md"):
        shutil.copy2(args.build_dir / name, args.output / name)
    shutil.copytree(args.build_dir / "engine", args.output / "engine", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(args.build_dir / "runtime", args.output / "runtime", ignore=ignored)
    shutil.copytree(args.site, args.output / "runtime/Lib/site-packages", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    python = str(args.output / "runtime/python.exe")
    subprocess.run([python, "-m", "pip", "check"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    pins = subprocess.check_output([python, "-m", "pip", "freeze"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    (args.output / "runtime/DEPENDENCIES.txt").write_text(pins, encoding="utf-8")
    code = "import json,torch,torchvision; assert torch.cuda.is_available(); print(json.dumps({'torch':torch.__version__,'torchvision':torchvision.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name()}))"
    report = json.loads(subprocess.check_output([python, "-c", code], text=True, creationflags=subprocess.CREATE_NO_WINDOW))
    report["source_index"] = "https://download.pytorch.org/whl/cu126"
    (args.output / "runtime/cuda-manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
