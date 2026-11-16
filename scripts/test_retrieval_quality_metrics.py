import pytest

from retrieval_quality_metrics import calibrate, matched_events, peak_matches, summarize, temporal_iou


def hit(video="one", start=1, end=3, peak=2, score=.8):
    return dict(video=video, start=start, end=end, peak_t=peak, score=score)


def row(present=True, score=.8, split="dev", correct=True):
    return dict(present=present, target="one", sequence="one", split=split, sampled=present,
                gt=[dict(video="one", start=1, end=3)] if present else [],
                hits=[hit(video="one" if correct else "wrong", score=score)])


def test_absence_is_a_false_accept_not_a_positive_recall_denominator():
    metrics = summarize([row(), row(False)])
    assert metrics["recall_at_1"] == 1
    assert metrics["absent_false_accept_rate"] == 1
    assert metrics["accepted_top1_precision"] == .5


def test_wrong_video_and_interval_endpoint_do_not_match():
    truth = dict(video="one", start=1, end=3)
    assert not peak_matches(hit(video="wrong"), truth)
    assert temporal_iou(hit(video="wrong"), truth) == 0
    assert peak_matches(hit(peak=1), truth)
    assert not peak_matches(hit(peak=3), truth)


def test_whole_video_hit_does_not_get_perfect_temporal_credit():
    sample = row()
    sample["hits"] = [hit(start=0, end=100)]
    metrics = summarize([sample])
    assert metrics["correct_top1"] == 1
    assert metrics["iou50_top1"] == 0
    assert metrics["mean_top1_iou"] == .02


def test_repeated_hits_cannot_count_one_event_twice():
    truth = [dict(video="one", start=1, end=3), dict(video="one", start=8, end=10)]
    assert matched_events([hit(), hit(), hit()], truth) == 1
    assert matched_events([hit(), hit(start=8, end=10, peak=9)], truth) == 2


def test_reject_and_wrong_accept_have_separate_counts():
    metrics = summarize([row(score=.2), row(score=.9, correct=False), row(False, score=.9)], .5)
    assert metrics["false_rejected_positive"] == 1
    assert metrics["wrong_accepted_positive_top1"] == 1
    assert metrics["false_accepted_absent"] == 1
    assert metrics["correct_top1"] == 0


def test_threshold_uses_only_dev_and_respects_budget():
    dev = [row(score=.9), row(score=.7), row(False, score=.8)]
    fitted = calibrate(dev)
    assert fitted["threshold"] == .9
    assert fitted["correct_top1"] == 1
    assert fitted["false_accepted_absent"] == 0
    assert summarize([row(False, score=.95, split="test")], fitted["threshold"])["false_accepted_absent"] == 1
    with pytest.raises(ValueError, match="development"):
        calibrate([*dev, row(split="test")])


def test_reject_all_is_valid_when_negatives_outscore_positives():
    fitted = calibrate([row(score=.7), row(False, score=.9)])
    assert fitted["threshold"] > .9
    assert fitted["correct_top1"] == 0
    assert fitted["accepted_queries"] == 0
