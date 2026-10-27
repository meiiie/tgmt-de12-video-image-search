"""Text -> moment search over a frame index (Đề 12).
Frame embeddings are the same ones the image search uses; a text query is embedded into the same space
(EmbeddingGemma 2: shared text/image space; SigLIP 2 / CLIP: get_text_features) and scored against every frame.
Temporal layer: per-video score curve -> moving-average smoothing -> segments; ordinal words pick the n-th
matching segment in time order instead of the best one."""
import re, time, numpy as np, torch

# ---------------- ordinal parsing (EN + VI) ----------------
_ORD = [  # (regex, ordinal) ; checked in order, longest first
    (r"\blần đầu tiên\b|\bđầu tiên\b|\blần thứ nhất\b|\bthứ nhất\b|\bfirst\b|\b1st\b", 1),
    (r"\blần thứ hai\b|\bthứ hai\b|\bthứ 2\b|\bsecond\b|\b2nd\b", 2),
    (r"\blần thứ ba\b|\bthứ ba\b|\bthứ 3\b|\bthird\b|\b3rd\b", 3),
    (r"\blần cuối cùng\b|\bcuối cùng\b|\blần cuối\b|\bcuối\b|\blast\b|\bfinal\b", -1),
]
def parse_ordinal(q):
    """'khoảnh khắc sút bóng vào lưới đầu tiên' -> ('khoảnh khắc sút bóng vào lưới', 1). Returns (clean_text, n|None)."""
    s = q.strip()
    for pat, n in _ORD:
        m = re.search(pat, s, flags=re.I)
        if m:
            clean = re.sub(r"\s+", " ", (s[:m.start()] + s[m.end():])).strip(" ,.")
            clean = re.sub(r"^(the|a)\s+time\s+", "", clean, flags=re.I)
            return (clean or s), n
    return s, None

# ---------------- text encoders ----------------
class TextEncoder:
    """Encodes queries into the frame index space. `emb` is the vsearch.core.Embedder that built the index
    (reused, so the model is loaded once)."""
    def __init__(self, emb, translate=None):
        self.emb = emb; self.tr = None
        if translate:  # 'opus' -> Helsinki-NLP/opus-mt-vi-en (local MarianMT, CPU)
            from transformers import MarianMTModel, MarianTokenizer
            n = "Helsinki-NLP/opus-mt-vi-en"; self.tt = MarianTokenizer.from_pretrained(n); self.tr = MarianMTModel.from_pretrained(n).eval()
    @torch.no_grad()
    def translate(self, texts):
        x = self.tt(texts, return_tensors="pt", padding=True)
        return self.tt.batch_decode(self.tr.generate(**x, num_beams=4, max_new_tokens=64), skip_special_tokens=True)
    @torch.no_grad()
    def __call__(self, texts):
        if self.tr is not None: texts = self.translate(texts)
        e = self.emb
        if e.kind == "st":
            return np.asarray(e.m.encode(texts, prompt_name="SearchQuery", normalize_embeddings=True), dtype="float32")
        if e.kind == "dino": raise ValueError("DINOv3 has no text encoder: rebuild the index with EG2/SigLIP2/CLIP")
        siglip = "siglip" in e.name.lower()
        x = e.p(text=texts, return_tensors="pt", padding="max_length" if siglip else True, truncation=True,
                **({"max_length": 64} if siglip else {}))
        x = {k: v.to(e.dev) for k, v in x.items() if k in ("input_ids", "attention_mask")}
        if siglip: x.pop("attention_mask", None)  # SigLIP text tower is trained without attention mask
        f = e.m.get_text_features(**x)
        if not isinstance(f, torch.Tensor): f = f.pooler_output
        return torch.nn.functional.normalize(f.float(), dim=-1).cpu().numpy()

# ---------------- temporal layer ----------------
def curves(meta, scores):
    """Per-video (times, scores) for frame vectors."""
    by = {}
    for m, s in zip(meta, scores):
        if m["kind"] == "frame": by.setdefault(m["video"], []).append((m["t"], float(s)))
    return {v: (np.array([t for t, _ in sorted(x)]), np.array([s for _, s in sorted(x)])) for v, x in by.items()}

def smooth(s, w):
    if w <= 1 or len(s) < 2: return s
    k = np.ones(w) / w; p = w // 2
    return np.convolve(np.pad(s, (p, w - 1 - p), mode="edge"), k, mode="valid")

def runs(t, s, thr, dt, min_len=1, gap=1):
    """Contiguous runs of s>=thr (gaps of <=gap frames bridged) -> [{start,end,peak_t,score}]."""
    on = np.where(s >= thr)[0]; out = []
    if len(on) == 0: return out
    grp = [[on[0]]]
    for i in on[1:]:
        (grp[-1].append(i) if i - grp[-1][-1] <= gap + 1 else grp.append([i]))
    for g in grp:
        if len(g) < min_len: continue
        j = g[int(np.argmax(s[g]))]
        out.append({"start": float(t[g[0]]), "end": float(t[g[-1]] + dt), "peak_t": float(t[j]), "score": float(s[j])})
    return out

def text_search(meta, X, q, fps, method="window", w=3, alpha=0.5, beta=0.5, ordinal=None, video=None, k=10, scores=None, ord_v2=None, Xdup=None):
    """method: 'frame' = top frames merged into segments (baseline); 'window' = smoothed curve + adaptive segment.
    ordinal: 1,2,3,-1 -> within the chosen video, candidate segments with score >= med+beta*(max-med) sorted by time.
    video: restrict to one video (the user 'loaded' it)."""
    sc = scores if scores is not None else X @ q.reshape(-1); C = curves(meta, sc); dt = 1.0 / fps
    if ordinal and ord_v2 is not None:  # v2 events: peaks relative to top, merged, replays removed
        segs = []
        for v, (t, s) in C.items():
            if video and v != video: continue
            ev = events_v2(t, smooth(s, w), dt, meta, v, Xdup, **ord_v2)
            n = ordinal - 1 if ordinal > 0 else ordinal
            pick = ev[n] if -len(ev) <= n < len(ev) else ev[-1]
            segs.append({"video": v, **pick, "n_candidates": len(ev)})
        return sorted(segs, key=lambda r: -r["score"])[:k]
    if video: C = {video: C[video]}
    if method == "proposals" and not ordinal:  # Charades-STA: multi-scale sliding windows, chosen on dev (README)
        segs = []
        for v, (t, s) in C.items():
            segs += [{"video": v, "start": a, "end": b, "peak_t": a + (b - a) / 2, "score": sc} for a, b, sc in window_proposals(t, s, float(t[-1]) + dt, dt)]
        return sorted(segs, key=lambda r: -r["score"])[:k]
    segs = []
    for v, (t, s) in C.items():
        ss = smooth(s, w if method == "window" else 1)
        if ordinal:
            med, mx = np.median(ss), ss.max()
            cand = sorted(runs(t, ss, med + beta * (mx - med), dt, min_len=2), key=lambda r: r["start"])
            if not cand: cand = runs(t, ss, mx, dt)
            n = ordinal - 1 if ordinal > 0 else ordinal
            pick = cand[n] if -len(cand) <= n < len(cand) else cand[-1]
            segs.append({"video": v, **pick, "n_candidates": len(cand)}); continue
        # non-ordinal: every local segment in this video, bounded at peak - alpha*(peak-median)
        med = np.median(ss); used = np.zeros(len(ss), bool)
        for j in np.argsort(-ss):
            if used[j] or len(segs) > 4 * k: break
            thr = ss[j] - alpha * (ss[j] - med); a = b = j
            while a > 0 and ss[a - 1] >= thr and not used[a - 1]: a -= 1
            while b < len(ss) - 1 and ss[b + 1] >= thr and not used[b + 1]: b += 1
            used[a:b + 1] = True
            segs.append({"video": v, "start": float(t[a]), "end": float(t[b] + dt), "peak_t": float(t[j]), "score": float(ss[j])})
    return sorted(segs, key=lambda r: -r["score"])[:k] if not ordinal else sorted(segs, key=lambda r: -r["score"])[:k]

def events_v2(t, ss, dt, meta=None, video=None, Xdup=None, rho=0.3, gap=2.0, dup=None, bound=0.5):
    """Order-word events (v2). Local maxima whose relative height (s-med)/(top-med) >= rho are candidate peaks
    (low-scoring events are kept unless below rho of the top peak); peaks closer than `gap` s are merged into one
    event (highest kept); an event whose peak frame embedding (Xdup, image space) has cosine >= dup with an
    EARLIER kept event's peak is treated as a replay and dropped. Events returned in time order."""
    med, top = np.median(ss), ss.max(); rel = (ss - med) / max(1e-9, top - med)
    pk = [i for i in range(len(ss)) if rel[i] >= rho and (i == 0 or ss[i] >= ss[i-1]) and (i == len(ss)-1 or ss[i] >= ss[i+1])]
    merged = []
    for i in pk:
        if merged and t[i] - t[merged[-1][-1]] <= gap: merged[-1].append(i)
        else: merged.append([i])
    peaks = [max(g, key=lambda i: ss[i]) for g in merged]
    if dup is not None and Xdup is not None:
        idx = {m["t"]: j for j, m in enumerate(meta) if m["video"] == video and m["kind"] == "frame"}
        keep = []
        for i in peaks:
            e = Xdup[idx[float(t[i])]] if float(t[i]) in idx else None
            if e is not None and any(float(Xdup[idx[float(t[k])]] @ e) >= dup for k in keep): continue
            keep.append(i)
        peaks = keep
    out = []
    for i in peaks:
        thr = ss[i] - bound * (ss[i] - med); a = b = i
        while a > 0 and ss[a-1] >= thr: a -= 1
        while b < len(ss)-1 and ss[b+1] >= thr: b += 1
        out.append({"start": float(t[a]), "end": float(t[b] + dt), "peak_t": float(t[i]), "score": float(ss[i])})
    return out

def window_proposals(t, s, dur, dt, lam=1.5, scales=(0.2, 0.3, 0.4), k=5, nms=0.5):
    """Multi-scale sliding windows (length = scale * video length), score = mean(in) - lam*mean(out), NMS.
    Params chosen on the Charades-STA dev split (results/charades_m1.json)."""
    n = len(s); cs = np.concatenate([[0], np.cumsum(s)]); tot = cs[-1]; c = []
    for r in scales:
        L = max(1, int(round(r * n)))
        for a in range(0, n - L + 1):
            mi = (cs[a + L] - cs[a]) / L; mo = (tot - (cs[a + L] - cs[a])) / max(1, n - L)
            c.append((float(t[a]), float(min(dur, t[a + L - 1] + dt)), float(mi - lam * mo)))
    out = []
    iou = lambda x, y: max(0, min(x[1], y[1]) - max(x[0], y[0])) / max(1e-9, max(x[1], y[1]) - min(x[0], y[0]))
    for x in sorted(c, key=lambda z: -z[2]):
        if all(iou(x, o) < nms for o in out): out.append(x)
        if len(out) == k: break
    return out
