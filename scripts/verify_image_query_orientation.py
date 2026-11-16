"""Check EXIF query equivalence with real EG2 against a read-only library snapshot.

This verifies input processing, not retrieval accuracy on an annotated benchmark.
Private media, database copies and reports belong in ignored outputs/ directories.
"""
import argparse
import base64
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from PIL import Image, ImageOps
from desktop.backend.library import Library
from desktop.backend.server import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    snapshot = Path(tempfile.mkdtemp(prefix="snapshot-", dir=args.output.resolve()))
    source = sqlite3.connect((args.library / "library.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    target = sqlite3.connect(snapshot / "library.sqlite3")
    try:
        source.backup(target)
        frame_count = source.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
    finally:
        source.close()
        target.close()
    library = Library(snapshot, start_worker=False)
    assert library.status()["summary"]["frames"] == frame_count > 0
    image = ImageOps.exif_transpose(Image.open(args.image)).convert("RGB")
    exif = Image.Exif()
    exif[274] = 6
    rotated = BytesIO()
    image.transpose(Image.Transpose.ROTATE_90).save(rotated, format="JPEG", quality=95, exif=exif)
    canonical = BytesIO()
    ImageOps.exif_transpose(Image.open(BytesIO(rotated.getvalue()))).save(canonical, format="PNG")
    token = "local-image-query-verification-token"
    results = {}
    with TestClient(create_app(library, token)) as client:
        for name, payload in [("canonical", canonical), ("exif_orientation_6", rotated)]:
            response = client.post("/search", headers={"Authorization": f"Bearer {token}"},
                                   json={"image": base64.b64encode(payload.getvalue()).decode(), "limit": 10})
            assert response.status_code == 200, response.text
            result = response.json()
            results[name] = {"indexed_frames": result["indexed_frames"], "results": [
                {key: item[key] for key in ("frame_id", "start", "end", "peak", "score")}
                for item in result["results"]]}
        assert results["canonical"] == results["exif_orientation_6"]
        report = {"verified": True, "scope": "Same displayed pixels produce the same ranked results through the actual image API; not an accuracy benchmark", "device": library.encoder.device,
                  "indexed_frames": frame_count, "runs": results}
    (args.output / "orientation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verified": True, "device": report["device"], "indexed_frames": frame_count,
                      "top_peak": results["canonical"]["results"][0]["peak"]}), flush=True)


if __name__ == "__main__":
    main()
