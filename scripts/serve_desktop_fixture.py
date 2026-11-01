"""Real local API/media server with deterministic embeddings for UI behavior tests."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from PIL import Image
import uvicorn
from desktop.backend.library import Library
from desktop.backend.server import create_app
from desktop.tests.test_library import ColorEncoder

root = Path(__file__).resolve().parents[1]
folder = Path(tempfile.mkdtemp(prefix="frameatlas-ui-", dir=root / "data"))
sources = folder / "sources"
sources.mkdir()
for name, color in [("red-square", (20, 20, 220)), ("blue-scene", (220, 30, 20))]:
    writer = cv2.VideoWriter(str(sources / f"{name}.avi"), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 180))
    for i in range(80):
        frame = np.full((180, 320, 3), color, dtype=np.uint8)
        cv2.putText(frame, f"{name} / {i / 10:.1f}s", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, .6, (240, 240, 230), 1)
        writer.write(frame)
    writer.release()
Image.new("RGB", (64, 64), "blue").save(root / "outputs/onboarding/ui-query.png")
mixed = Image.new("RGB", (320, 180), "blue")
mixed.paste("red", (0, 0, 80, 180))
mixed.save(root / "outputs/onboarding/ui-query-mixed.png")
library = Library(folder / "library", ColorEncoder(), start_worker=False)
library.import_paths([str(sources)])
for video in library.store.videos():
    library.index_video(video)
uvicorn.run(create_app(library, "frameatlas-ui-test-token-01234567890123456789"), host="127.0.0.1", port=18765, log_level="warning")
