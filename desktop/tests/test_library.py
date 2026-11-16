import base64
from io import BytesIO

import cv2
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest

from desktop.backend.library import Library
from desktop.backend.media import export_clip
from desktop.backend.server import create_app


class ColorEncoder:
    """Deterministic fixture. Real EG2 has a separate integration probe."""
    signature = "test-rgb-v1"
    state, error, device = "ready", "", "cpu"

    def ensure(self):
        pass

    def images(self, images):
        vectors = np.array([np.asarray(image).mean(axis=(0, 1)) for image in images], dtype="float32")
        return vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)

    def query(self, text=None, image=None):
        return self.images([image])[0] if image else np.array([1, 0, 0], dtype="float32")


@pytest.fixture
def media(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    paths = []
    for name, color in [("red", (0, 0, 255)), ("blue", (255, 0, 0))]:
        path = directory / f"{name}.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 64))
        assert writer.isOpened()
        for _ in range(60):
            writer.write(np.full((64, 64, 3), color, dtype=np.uint8))
        writer.release()
        paths.append(path)
    return paths


@pytest.fixture
def library(tmp_path):
    lib = Library(tmp_path / "library", ColorEncoder(), start_worker=False)
    yield lib
    lib.close()


def index_all(library, media):
    library.import_paths([str(path) for path in media])
    for video in library.store.videos():
        library.index_video(video)


def test_per_video_counts_are_before_result_limit_and_include_zero(library, media):
    index_all(library, media)
    response = library.search(image=Image.new("RGB", (64, 64), "red"), limit=1, min_score=.9)
    counts = {v["name"]: v for v in response["per_video"]}
    assert len(response["results"]) == 1
    assert counts["red.avi"]["indexed_frames"] == 6
    assert counts["red.avi"]["similar_frames"] == 6
    assert counts["blue.avi"]["similar_frames"] == 0
    assert sum(v["indexed_frames"] for v in counts.values()) == response["indexed_frames"] == 12
    assert response["timings"]["score_ms"] >= 0
    red = next(v for v in library.store.videos() if v["name"] == "red.avi")
    narrow = library.search(image=Image.new("RGB", (64, 64), "red"), video_id=red["id"], start=2, end=4)
    assert len(narrow["per_video"]) == 1 and narrow["per_video"][0]["indexed_frames"] == 2


def test_prefetch_preserves_frames_and_records_only_committed_work(tmp_path, media):
    snapshots = []
    for prefetch in (False, True):
        lib = Library(tmp_path / str(prefetch), ColorEncoder(), start_worker=False)
        lib.store.update_settings({"prefetch": prefetch, "batch_size": 2})
        lib.import_paths([str(media[0])])
        lib.index_video(lib.store.videos()[0])
        with lib.store.connect() as db:
            snapshots.append(list(map(tuple, db.execute("SELECT t,embedding FROM frames ORDER BY t"))))
        video = lib.store.videos()[0]
        assert video["measured_frames"] == video["frames"] == 6
        assert video["index_seconds"] > 0 and video["decode_seconds"] > 0
        assert video["encode_seconds"] > 0 and video["write_seconds"] > 0
        lib.close()
    assert snapshots[0] == snapshots[1]
    changed_encoder = ColorEncoder()
    changed_encoder.signature = "changed-model-for-migration-check"
    reopened = Library(lib.root, changed_encoder, start_worker=False)
    video = reopened.store.videos()[0]
    assert video["frames"] == 0 and video["index_seconds"] is None
    reopened.close()


def test_import_deduplicates_folder_and_files(library, media):
    report = library.import_paths([str(media[0].parent), str(media[0])])
    assert report["added"] == report["discovered"] == 2
    assert library.import_paths([str(media[0])])["added"] == 0
    assert len(library.store.videos()) == 2


def test_search_play_save_restart_and_remove_preserves_original(library, media):
    index_all(library, media)
    results = library.search(text="red square")["results"]
    assert results[0]["name"] == "red.avi"
    assert library.search(image=Image.new("RGB", (64, 64), "blue"))["results"][0]["name"] == "blue.avi"
    first = results[0]
    identity = library.save_moment(first["video_id"], 1, 3, 2, "Keep this")
    reopened = Library(library.root, ColorEncoder(), start_worker=False)
    assert reopened.moments()[0]["id"] == identity
    assert reopened.moments()[0]["frame_id"] is not None
    assert reopened.search(text="red")["results"][0]["video_id"] == first["video_id"]
    reopened.job(first["video_id"], "remove")
    assert reopened.moments() == []
    assert media[0].is_file()
    assert len(reopened.store.videos()) == 1
    reopened.close()


def test_pause_checkpoint_and_restart_resume_without_duplicate_frames(library, media):
    library.import_paths([str(media[0])])
    video = library.store.videos()[0]
    original = library.encoder.images
    calls = 0
    def pausing(images):
        nonlocal calls
        calls += 1
        if calls == 2:
            library.store.update_settings({"paused": True})
        return original(images)
    library.encoder.images = pausing
    library.index_video(video)
    current = library.store.video(video["id"])
    assert current["status"] == "queued"
    assert current["frames"] == 2
    assert current["next_t"] == 2
    reopened = Library(library.root, ColorEncoder(), start_worker=False)
    reopened.settings({"paused": False})
    reopened.index_video(reopened.store.video(video["id"]))
    final = reopened.store.video(video["id"])
    assert final["status"] == "ready" and final["frames"] == 6
    with reopened.store.connect() as db:
        assert [r[0] for r in db.execute("SELECT t FROM frames ORDER BY t")] == [0, 1, 2, 3, 4, 5]
    reopened.close()


def test_cancel_during_inference_cannot_commit(library, media):
    library.import_paths([str(media[0])])
    video = library.store.videos()[0]
    original = library.encoder.images
    def cancel(images):
        library.job(video["id"], "cancel")
        return original(images)
    library.encoder.images = cancel
    library.index_video(video)
    current = library.store.video(video["id"])
    assert current["status"] == "cancelled"
    assert current["frames"] == 0


def test_pause_during_final_batch_does_not_mark_incomplete_index_ready(library, media):
    library.import_paths([str(media[0])])
    library.store.update_settings({"batch_size": 16})
    video = library.store.videos()[0]
    original = library.encoder.images
    def pause_final(images):
        library.store.update_settings({"paused": True})
        return original(images)
    library.encoder.images = pause_final
    library.index_video(video)
    current = library.store.video(video["id"])
    assert current["status"] == "queued"
    assert current["frames"] == 0
    library.encoder.images = original
    library.settings({"paused": False})
    library.index_video(current)
    final = library.store.video(video["id"])
    assert final["status"] == "ready" and final["frames"] == 6


def test_changed_video_invalidates_embeddings(library, media):
    index_all(library, media)
    with media[0].open("ab") as file:
        file.write(b"source changed")
    assert library.rescan()["added"] == 1
    red = next(v for v in library.store.videos() if v["name"] == "red.avi")
    assert red["status"] == "queued" and red["frames"] == 0
    assert all(r["name"] != "red.avi" for r in library.search(text="red")["results"])


def test_corrupt_and_missing_video_have_visible_error(library, media):
    corrupt = media[0].parent / "corrupt.mp4"
    corrupt.write_bytes(b"not a video")
    library.import_paths([str(corrupt), str(media[0])])
    media[0].unlink()
    for video in library.store.videos():
        library.index_video(video)
    assert all(v["status"] == "error" and v["error"] for v in library.store.videos())


def test_export_is_playable_accurate_and_never_overwrites(library, media, tmp_path):
    index_all(library, media)
    video = library.store.videos()[0]
    target = tmp_path / "clip.mp4"
    export_clip(video, 1, 3, target)
    cap = cv2.VideoCapture(str(target))
    assert cap.isOpened()
    assert abs(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) - 2) < .15
    assert cap.read()[0]
    cap.release()
    contents = target.read_bytes()
    with pytest.raises(ValueError):
        export_clip(video, 0, 1, target)
    assert target.read_bytes() == contents
    with pytest.raises(ValueError):
        export_clip(video, -1, 3, tmp_path / "bad.mp4")


def test_api_auth_validation_thumbnails_and_video_ranges(library, media):
    index_all(library, media)
    token = "t" * 64
    with TestClient(create_app(library, token)) as client:
        assert client.get("/library").status_code == 401
        assert client.get(f"/library?token={token}").status_code == 401
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/library", headers={**headers, "Origin": "https://example.com"}).status_code == 403
        assert client.get("/library", headers=headers).status_code == 200
        assert client.post("/search", headers=headers, json={}).status_code == 422
        assert client.post("/search", headers=headers, json={"text": "a", "image": "bad"}).status_code == 422
        assert client.post("/search", headers=headers, json={"image": "!!!!"}).status_code == 400
        assert client.patch("/settings", headers=headers, json={"fps": 0}).status_code == 422
        results = client.post("/search", headers=headers, json={"text": "red"}).json()["results"]
        frame = results[0]["frame_id"]
        identity = results[0]["video_id"]
        assert client.get(f"/thumbnails/{frame}?token={token}").headers["content-type"] == "image/jpeg"
        response = client.get(f"/media/{identity}?token={token}", headers={"Range": "bytes=0-99"})
        assert response.status_code == 206 and len(response.content) == 100
        assert client.get(f"/videos/missing", headers=headers).status_code == 404


@pytest.mark.parametrize("orientation,transform", [(2, Image.Transpose.FLIP_LEFT_RIGHT), (6, Image.Transpose.ROTATE_90)])
def test_image_search_uses_displayed_exif_orientation(library, media, orientation, transform):
    class LeftEdgeEncoder(ColorEncoder):
        def images(self, images):
            return super().images([image.crop((0, 0, max(1, image.width // 5), image.height)) for image in images])

    library.encoder = LeftEdgeEncoder()
    index_all(library, media)
    displayed = Image.new("RGB", (100, 60), "blue")
    displayed.paste("red", (0, 0, 25, 60))
    stored = displayed.transpose(transform)
    exif = Image.Exif()
    exif[274] = orientation
    payload = BytesIO()
    stored.save(payload, format="JPEG", quality=95, exif=exif)
    token = "t" * 64
    with TestClient(create_app(library, token)) as client:
        response = client.post("/search", headers={"Authorization": f"Bearer {token}"},
                               json={"image": base64.b64encode(payload.getvalue()).decode()})
        assert response.status_code == 200
        assert response.json()["results"][0]["name"] == "red.avi"


def test_settings_reset_and_active_job_conflict(library, media):
    index_all(library, media)
    library.active = library.store.videos()[0]["id"]
    with pytest.raises(ValueError):
        library.settings({"fps": 2})
    library.active = None
    library.settings({"fps": 2})
    assert all(v["frames"] == 0 and v["status"] == "queued" for v in library.store.videos())
    assert library.search(text="red")["results"] == []


def test_interrupted_indexing_recovers_at_startup(library, media):
    library.import_paths([str(media[0])])
    with library.store.connect() as db:
        db.execute("UPDATE videos SET status='indexing'")
    reopened = Library(library.root, ColorEncoder(), start_worker=False)
    assert reopened.store.videos()[0]["status"] == "queued"
    reopened.close()


def test_sparse_index_reports_duration_and_resumes_at_decoded_timestamp(library, media):
    library.store.update_settings({"fps": .5, "batch_size": 1})
    library.import_paths([str(media[0])])
    video = library.store.videos()[0]
    original = library.encoder.images
    observations = []

    def pause_second_batch(images):
        observations.append(library.status())
        if len(observations) == 2:
            library.store.update_settings({"paused": True})
        return original(images)

    library.encoder.images = pause_second_batch
    library.index_video(video)
    assert observations[0]["videos"][0]["duration"] == 6
    assert observations[0]["progress"]["total"] == 3
    assert observations[1]["progress"]["processed"] == 1
    assert observations[1]["progress"]["rate"] > 0
    assert observations[1]["progress"]["eta_seconds"] >= 0
    paused = library.store.video(video["id"])
    assert paused["frames"] == 1 and paused["next_t"] == 2
    assert library.status()["progress"] is None

    reopened = Library(library.root, ColorEncoder(), start_worker=False)
    reopened.settings({"paused": False})
    reopened.index_video(reopened.store.video(video["id"]))
    assert reopened.store.video(video["id"])["status"] == "ready"
    with reopened.store.connect() as db:
        assert [r[0] for r in db.execute("SELECT t FROM frames ORDER BY t")] == [0, 2, 4]
    reopened.close()


@pytest.mark.parametrize("image_query,fps", [(True, 1), (False, .1)])
def test_brief_exact_match_beats_sustained_weaker_match(library, media, image_query, fps):
    index_all(library, media)
    library.store.update_settings({"fps": fps})
    with library.store.connect() as db:
        red = next(v for v in library.store.videos() if v["name"] == "red.avi")
        blue = next(v for v in library.store.videos() if v["name"] == "blue.avi")
        db.execute("UPDATE frames SET embedding=? WHERE video_id=?", (np.array([0, 0, 1], dtype="float32").tobytes(), red["id"]))
        db.execute("UPDATE frames SET embedding=? WHERE video_id=? AND t=2", (np.array([1, 0, 0], dtype="float32").tobytes(), red["id"]))
        db.execute("UPDATE frames SET embedding=? WHERE video_id=?", (np.array([.8, .6, 0], dtype="float32").tobytes(), blue["id"]))
        db.execute("UPDATE frames SET t=t/?", (fps,))
        db.execute("UPDATE videos SET duration=6/?", (fps,))
    result = library.search(image=Image.new("RGB", (64, 64), "red")) if image_query else library.search(text="red square")
    assert result["results"][0]["video_id"] == red["id"]
    assert result["results"][0]["peak"] == 2 / fps


def test_time_scope_filters_before_ranking_and_clips_segment_bounds(library, media):
    index_all(library, media)
    video = library.store.videos()[0]
    with TestClient(create_app(library, "t" * 64)) as client:
        headers = {"Authorization": "Bearer " + "t" * 64}
        body = {"text": "red", "video_id": video["id"], "start": 2, "end": 3.5}
        response = client.post("/search", headers=headers, json=body)
        assert response.status_code == 200
        result = response.json()
        assert result["indexed_frames"] == 2
        assert result["results"]
        assert all(r["video_id"] == video["id"] and 2 <= r["start"] <= r["peak"] < r["end"] <= 3.5 for r in result["results"])
        assert client.post("/search", headers=headers, json={**body, "start": 10, "end": 20}).json()["results"] == []
        assert client.post("/search", headers=headers, json={**body, "video_id": None}).status_code == 422
        assert client.post("/search", headers=headers, json={**body, "end": 1}).status_code == 422
