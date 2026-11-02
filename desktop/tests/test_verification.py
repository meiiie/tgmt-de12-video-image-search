import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO
from fastapi.testclient import TestClient

from desktop.backend.verification import compare_features, extract_features
from desktop.backend.library import Library
from desktop.backend.server import create_app
from desktop.tests.test_library import ColorEncoder


def textured(seed=1):
    rng = np.random.default_rng(seed)
    rgb = np.full((300, 400, 3), 225, dtype=np.uint8)
    for _ in range(100):
        x, y = rng.integers([10, 10], [390, 290])
        color = tuple(int(v) for v in rng.integers(0, 200, 3))
        cv2.circle(rgb, (x, y), int(rng.integers(2, 12)), color, -1)
    return rgb


def test_detail_correspondence_survives_crop_scale_and_translation():
    source = textured()
    target = np.full((500, 700, 3), 100, np.uint8)
    target[80:380, 150:550] = source
    crop = Image.fromarray(source).crop((45, 30, 345, 270)).resize((360, 288))
    result = compare_features(extract_features(crop), extract_features(Image.fromarray(target)))
    assert result["status"] == "matched"
    assert result["inliers"] >= 10


def test_unrelated_texture_and_flat_images_are_not_confirmed():
    query = extract_features(Image.fromarray(textured()))
    assert compare_features(query, extract_features(Image.fromarray(textured(22))))["status"] == "unconfirmed"
    flat = extract_features(Image.new("RGB", (200, 200), "red"))
    assert compare_features(flat, flat)["reason"] == "insufficient_detail"


def test_matching_one_small_corner_does_not_confirm_a_whole_image():
    a, b = textured(3), textured(19)
    b[:65, :70] = a[:65, :70]
    result = compare_features(extract_features(Image.fromarray(a)), extract_features(Image.fromarray(b)))
    assert result["status"] == "unconfirmed"


def test_detail_api_rejects_unrelated_candidates_and_retains_similar_search(tmp_path):
    lib = Library(tmp_path / "library", ColorEncoder(), start_worker=False)
    for seed in (1, 22):
        path = tmp_path / f"texture-{seed}.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (400, 300))
        for _ in range(20):
            writer.write(cv2.cvtColor(textured(seed), cv2.COLOR_RGB2BGR))
        writer.release()
        lib.import_paths([str(path)])
    for video in lib.store.videos():
        lib.index_video(video)
        assert lib.store.video(video["id"])["status"] == "ready"
    def payload(seed):
        stream = BytesIO()
        Image.fromarray(textured(seed)).save(stream, format="PNG")
        return base64.b64encode(stream.getvalue()).decode()
    headers = {"Authorization": "Bearer " + "t" * 64}
    with TestClient(create_app(lib, "t" * 64)) as client:
        same = client.post("/search", headers=headers, json={"image": payload(1), "image_mode": "detail"}).json()
        assert same["results"] and all(r["name"] == "texture-1.avi" for r in same["results"])
        absent = client.post("/search", headers=headers, json={"image": payload(99), "image_mode": "detail"}).json()
        assert absent["results"] == [] and absent["verification"]["checked"] > 0
        broad = client.post("/search", headers=headers, json={"image": payload(99), "image_mode": "similar"}).json()
        assert broad["results"]
        assert client.post("/search", headers=headers, json={"text": "red", "image_mode": "detail"}).status_code == 422
