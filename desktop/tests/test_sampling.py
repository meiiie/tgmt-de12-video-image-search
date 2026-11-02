import json

import cv2
import numpy as np
from PIL import Image
import pytest

from desktop.backend.library import Library
from desktop.backend.moments import hybrid_segments
from desktop.backend.sampling import frame_plan, scene_cuts
from desktop.tests.test_library import ColorEncoder


@pytest.fixture
def brief_scene(tmp_path):
    path = tmp_path / "brief.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20, (128, 96))
    for i in range(80):
        writer.write(np.full((96, 128, 3), (0, 0, 255) if 23 <= i < 29 else (255, 0, 0), dtype=np.uint8))
    writer.release()
    return path


def test_hybrid_finds_brief_scene_between_uniform_anchors(tmp_path, brief_scene):
    for mode in ("uniform", "hybrid"):
        lib = Library(tmp_path / mode, ColorEncoder(), start_worker=False)
        lib.store.update_settings({"fps": .5, "sampling": mode})
        lib.import_paths([str(brief_scene)])
        lib.index_video(lib.store.videos()[0])
        video = lib.store.videos()[0]
        assert video["status"] == "ready", video["error"]
        with lib.store.connect() as db:
            times = [r[0] for r in db.execute("SELECT t FROM frames ORDER BY t")]
        assert {0, 2}.issubset(times)
        assert any(1.15 <= t < 1.45 for t in times) == (mode == "hybrid")
        if mode == "hybrid":
            hit = lib.search(image=Image.new("RGB", (50, 50), "red"))["results"][0]
            assert 1.15 <= hit["peak"] < 1.45
            assert hit["start"] >= 1.15 and hit["end"] <= 1.45
        lib.close()


def test_scan_cancel_leaves_no_completed_cache(tmp_path, brief_scene):
    cache = tmp_path / "cuts.json"
    with pytest.raises(InterruptedError):
        scene_cuts(brief_scene, cache, current=lambda: False)
    assert not cache.exists()
    cuts = scene_cuts(brief_scene, cache)
    assert len(cuts) == 2
    assert json.loads(cache.read_text())["cuts"] == cuts
    plan = frame_plan(80, 20, .5, cuts)
    assert len({p["frame"] for p in plan}) == len(plan)


def test_hybrid_pause_resume_keeps_identical_frames_and_boundaries(tmp_path, brief_scene):
    lib = Library(tmp_path / "library", ColorEncoder(), start_worker=False)
    lib.store.update_settings({"fps": .5, "sampling": "hybrid", "batch_size": 1})
    lib.import_paths([str(brief_scene)])
    video = lib.store.videos()[0]
    original, calls = lib.encoder.images, [0]
    def pause(images):
        calls[0] += 1
        if calls[0] == 2:
            lib.store.update_settings({"paused": True})
        return original(images)
    lib.encoder.images = pause
    lib.index_video(video)
    first = lib.store.video(video["id"])
    assert first["frames"] == 1 and first["status"] == "queued", first["error"]
    resumed = Library(lib.root, ColorEncoder(), start_worker=False)
    resumed.settings({"paused": False})
    resumed.index_video(resumed.store.video(video["id"]))
    final = resumed.store.video(video["id"])
    assert final["status"] == "ready", final["error"]
    with resumed.store.connect() as db:
        records = [tuple(r) for r in db.execute("SELECT t,shot_start,shot_end FROM frames ORDER BY t")]
    assert len(records) == final["total"] == len({r[0] for r in records})
    assert all(a <= t < b for t, a, b in records)
    lib.close()
    resumed.close()


def test_irregular_text_and_image_segments_do_not_cross_shots():
    rows = [dict(video_id="one", t=t, shot_start=a, shot_end=b)
            for t, a, b in [(0, 0, 2), (1.8, 0, 2), (2, 2, 3), (2.1, 2, 3), (2.8, 2, 3)]]
    for text in (False, True):
        hits = hybrid_segments(rows, np.ones(5), text=text, limit=10)
        assert {(h["start"], h["end"]) for h in hits} == {(0, 2), (2, 3)}
        assert all(h["start"] <= h["peak_t"] < h["end"] for h in hits)


def test_hybrid_ordinal_ignores_low_similarity_shots():
    rows = [dict(video_id="one", t=t, shot_start=t, shot_end=t+1) for t in range(5)]
    scores = np.array([.1, .1, .9, .1, .1])
    first = hybrid_segments(rows, scores, text=True, limit=10, ordinal=1)
    assert len(first) == 1 and first[0]["peak_t"] == 2
    assert hybrid_segments(rows, scores, text=True, limit=10, ordinal=2) == []
    assert hybrid_segments(rows, np.ones(5), text=True, limit=10, ordinal=1) == []
