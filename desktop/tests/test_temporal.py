import numpy as np

from vsearch.text import text_search


def test_missing_nth_event_never_silently_returns_last_event():
    meta = [{"kind": "frame", "video": "clip", "t": float(i)} for i in range(5)]
    result = text_search(meta, None, None, 1, scores=np.array([0, .9, 0, 0, 0]), w=1, ordinal=3, ord_v2={"rho": .3, "gap": 1, "dup": None})
    assert result == []


def test_global_top_survives_many_earlier_videos():
    meta = [{"kind": "frame", "video": str(i), "t": 0.0} for i in range(100)]
    result = text_search(meta, None, None, 1, scores=np.linspace(0, 1, 100), k=1)
    assert result[0]["video"] == "99"
