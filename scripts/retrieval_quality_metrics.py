"""Retrieval metrics with explicit absent queries and half-open time intervals."""
import math


def peak_matches(hit, truth):
    return hit["video"] == truth["video"] and truth["start"] <= hit["peak_t"] < truth["end"]


def temporal_iou(hit, truth):
    if hit["video"] != truth["video"]:
        return 0.0
    overlap = max(0.0, min(hit["end"], truth["end"]) - max(hit["start"], truth["start"]))
    union = hit["end"] - hit["start"] + truth["end"] - truth["start"] - overlap
    return overlap / union if union > 0 else 0.0


def matched_events(hits, truths):
    """Maximum one-to-one matching; repeated hits cannot inflate event recall."""
    assigned = {}

    def assign(i, visited):
        for j, truth in enumerate(truths):
            if j in visited or temporal_iou(hits[i], truth) < 0.5:
                continue
            visited.add(j)
            if j not in assigned or assign(assigned[j], visited):
                assigned[j] = i
                return True
        return False

    for i in range(len(hits)):
        assign(i, set())
    return len(assigned)


def summarize(rows, threshold=-1.0):
    positive = [r for r in rows if r["present"]]
    negative = [r for r in rows if not r["present"]]
    counts = dict(positive_queries=len(positive), absent_queries=len(negative),
                  positive_targets=len({r["target"] for r in positive}),
                  absent_targets=len({r["target"] for r in negative}),
                  positive_sources=len({r["sequence"] for r in positive}),
                  absent_sources=len({r["sequence"] for r in negative}),
                  sampled_positive_queries=sum(r["sampled"] for r in positive),
                  correct_top1=0, correct_top5=0, iou50_top1=0, iou50_top5=0,
                  false_rejected_positive=0, wrong_accepted_positive_top1=0,
                  false_accepted_absent=0, accepted_queries=0)
    ious, event_recalls = [], []
    for row in rows:
        hits = [h for h in row["hits"] if h["score"] >= threshold]
        counts["accepted_queries"] += bool(hits)
        if not row["present"]:
            assert not row["gt"]
            counts["false_accepted_absent"] += bool(hits)
            continue
        assert row["gt"]
        correct1 = any(peak_matches(h, g) for h in hits[:1] for g in row["gt"])
        correct5 = any(peak_matches(h, g) for h in hits[:5] for g in row["gt"])
        counts["correct_top1"] += correct1
        counts["correct_top5"] += correct5
        counts["false_rejected_positive"] += not hits
        counts["wrong_accepted_positive_top1"] += bool(hits) and not correct1
        best1 = max((temporal_iou(h, g) for h in hits[:1] for g in row["gt"]), default=0.0)
        best5 = max((temporal_iou(h, g) for h in hits[:5] for g in row["gt"]), default=0.0)
        counts["iou50_top1"] += best1 >= .5
        counts["iou50_top5"] += best5 >= .5
        ious.append(best1)
        event_recalls.append(matched_events(hits[:5], row["gt"]) / len(row["gt"]))
    p, n = len(positive), len(negative)
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None
    tp = counts["correct_top1"]
    fp = counts["wrong_accepted_positive_top1"] + counts["false_accepted_absent"]
    return {**counts, "threshold": threshold,
            "sampling_coverage": ratio(counts["sampled_positive_queries"], p),
            "recall_at_1": ratio(tp, p), "recall_at_5": ratio(counts["correct_top5"], p),
            "miss_at_5": ratio(p - counts["correct_top5"], p),
            "absent_false_accept_rate": ratio(counts["false_accepted_absent"], n),
            "accepted_top1_precision": ratio(tp, counts["accepted_queries"]),
            "correct_top1_f1": ratio(2 * tp, 2 * tp + fp + p - tp),
            "mean_top1_iou": ratio(sum(ious), p), "macro_event_recall_at_5_iou50": ratio(sum(event_recalls), p)}


def calibrate(dev_rows, absent_budget=.05):
    if not dev_rows or any(r["split"] != "dev" for r in dev_rows):
        raise ValueError("Calibration accepts development queries only")
    if not any(not r["present"] for r in dev_rows) or not any(r["present"] for r in dev_rows):
        raise ValueError("Calibration needs present and absent development queries")
    scores = [r["hits"][0]["score"] for r in dev_rows if r["hits"]]
    candidates = sorted({-1.0, *scores, math.nextafter(max(scores, default=1.0), math.inf)})
    eligible = []
    for threshold in candidates:
        metrics = summarize(dev_rows, threshold)
        if metrics["absent_false_accept_rate"] <= absent_budget:
            wrong = metrics["wrong_accepted_positive_top1"] + metrics["false_accepted_absent"]
            eligible.append((metrics["correct_top1"], -wrong, threshold, metrics))
    return max(eligible, key=lambda item: item[:3])[3]
