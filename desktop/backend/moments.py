"""Temporal proposals for irregular sampling; shot boundaries are hard limits."""
import numpy as np


def hybrid_segments(rows, scores, *, text, limit, ordinal=None):
    groups = {}
    for row, score in zip(rows, scores):
        key = (row["video_id"], row["shot_start"], row["shot_end"])
        if key[1] is None or key[2] is None:
            raise ValueError("Chỉ mục chuyển cảnh thiếu mốc; hãy lập chỉ mục lại")
        groups.setdefault(key, []).append((row["t"], float(score)))
    segments, video_values = [], {}
    for (video, start, end), samples in groups.items():
        samples.sort()
        times, values = np.asarray(samples).T
        edges = np.concatenate(([start], (times[:-1] + times[1:]) / 2, [end]))
        if text:
            smoothed = []
            for t in times:
                weights = np.maximum(0, np.minimum(edges[1:], t + 1.5) - np.maximum(edges[:-1], t - 1.5))
                smoothed.append(float(values @ weights / weights.sum()))
            values = np.asarray(smoothed)
        if ordinal:
            video_values.setdefault(video, []).extend(values)
        median, used = np.median(values), np.zeros(len(values), bool)
        for j in np.argsort(-values, kind="stable"):
            if used[j]:
                continue
            threshold = values[j] - .35 * (values[j] - median)
            a = b = j
            while a > 0 and not used[a-1] and values[a-1] >= threshold:
                a -= 1
            while b + 1 < len(values) and not used[b+1] and values[b+1] >= threshold:
                b += 1
            used[a:b+1] = True
            segments.append({"video": video, "start": float(edges[a]), "end": float(edges[b+1]),
                             "peak_t": float(times[j]), "score": float(values[j])})
    if ordinal:
        if not segments:
            return []
        video = max(segments, key=lambda s: s["score"])["video"]
        values = np.asarray(video_values[video])
        median, top = np.median(values), values.max()
        if top - median < 1e-9:
            return []
        candidates = sorted((s for s in segments if s["video"] == video and s["score"] >= median + .3 * (top - median)),
                            key=lambda s: s["peak_t"])
        groups = []
        for candidate in candidates:
            if groups and candidate["peak_t"] - groups[-1][-1]["peak_t"] <= 1:
                groups[-1].append(candidate)
            else:
                groups.append([candidate])
        ordered = [max(group, key=lambda s: s["score"]) for group in groups]
        index = ordinal - 1 if ordinal > 0 else ordinal
        return [ordered[index]] if -len(ordered) <= index < len(ordered) else []
    return sorted(segments, key=lambda s: -s["score"])[:limit]
