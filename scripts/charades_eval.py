"""Charades-STA (small subset, fixed dev/test split) text->moment evaluation, video given (standard STA setting).
Metrics (standard): R@1 and R@5 at temporal IoU 0.5 / 0.7, mIoU of the top-1, latency per query (text encode + search, CPU).
Methods:  baseline = current app pipeline (window w=3 smoothed frame scores, segments around peaks).
          prop     = multi-scale sliding-window proposals, score = mean(in) - lam*mean(out) on smoothed scores, NMS.
Parameters chosen on dev only (grid), reported on test. Usage: python scripts/charades_eval.py"""
import json, sys, time, itertools, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from vsearch.core import Embedder
from vsearch.text import TextEncoder, text_search, curves, smooth
from text_eval import load
Q = json.load(open("eval_charades/queries.json"))["queries"]
MODELS = {"eg2": ("google/embeddinggemma-2", "embeddinggemma-2"), "sig": ("google/siglip2-base-patch16-224", "siglip2-base-patch16-224")}
IDX = {m: load(f"data/text_idx/{t}_charades") for m, (_, t) in MODELS.items()}
def iou(a, b):
    i = max(0, min(a[1], b[1]) - max(a[0], b[0])); u = max(a[1], b[1]) - min(a[0], b[0]); return i / u if u > 0 else 0
def nms(c, thr=0.5, k=5):
    out = []
    for s in sorted(c, key=lambda x: -x[2]):
        if all(iou(s, o) < thr for o in out): out.append(s)
        if len(out) == k: break
    return out
def proposals(t, s, dur, lam=1.0, scales=(0.1, 0.2, 0.3, 0.4, 0.5), w=1):
    ss = smooth(s, w); n = len(ss); cs = np.concatenate([[0], np.cumsum(ss)]); tot = cs[-1]; out = []
    for r in scales:
        L = max(1, int(round(r * n)))
        for a in range(0, n - L + 1):
            mi = (cs[a + L] - cs[a]) / L; mo = (tot - (cs[a + L] - cs[a])) / max(1, n - L)
            out.append((float(t[a]), float(min(dur, t[a + L - 1] + 1.0)), mi - lam * mo))
    return nms(out)
def baseline(meta, sc, video, fps):
    return [(x["start"], x["end"], x["score"]) for x in text_search(meta, None, None, fps, scores=sc, video=video, k=5)]
ENC = {}
def encoders():
    if not ENC:
        for m, (n, _) in MODELS.items(): ENC[m] = TextEncoder(Embedder(n, device="cpu"))
    return ENC
_cache = {}
def emb(m, text):
    k = (m, text)
    if k not in _cache:
        t = time.time(); _cache[k] = (encoders()[m]([text])[0], (time.time() - t) * 1000)
    return _cache[k]
def scores(model, text, G, w):
    if model in MODELS: e, ms = emb(model, text); return IDX[model][1] @ e, ms
    eE, m1 = emb("eg2", text); eS, m2 = emb("sig", text)  # fusion 'fuse': global z
    zE = (IDX["eg2"][1] @ eE - G["eg2"][0]) / G["eg2"][1]; zS = (IDX["sig"][1] @ eS - G["sig"][0]) / G["sig"][1]
    return w * zE + (1 - w) * zS, m1 + m2
def evaluate(split, model, method, lang="en", G=None, w=0.5, translate=None, **kw):
    meta = IDX["eg2"][0]["meta"]; fps = IDX["eg2"][0]["fps"]; R = {"r1_5": [], "r1_7": [], "r5_5": [], "r5_7": [], "miou": [], "ms": []}
    for q in [q for q in Q if q["split"] == split]:
        text = q[lang]; t0 = time.time(); tr_ms = 0
        if translate: text, tr_ms = translate(text)
        sc, enc_ms = scores(model, text, G, w); t1 = time.time()
        if method == "baseline": segs = baseline(meta, sc, q["video"], fps)
        else:
            tt, ss = curves(meta, sc)[q["video"]]; segs = proposals(tt, ss, q["duration"], **kw)
        gt = (q["start"], q["end"]); ious = [iou(s, gt) for s in segs]
        R["r1_5"].append(ious[0] >= .5); R["r1_7"].append(ious[0] >= .7); R["r5_5"].append(max(ious) >= .5); R["r5_7"].append(max(ious) >= .7)
        R["miou"].append(ious[0]); R["ms"].append(enc_ms + tr_ms + (time.time() - t1) * 1000)
    return {k: round(float(np.mean(v)) * (1 if k == "ms" else 100), 2) for k, v in R.items()} | {"n": len(R["ms"])}
if __name__ == "__main__":
    G = {}
    for m in MODELS:  # global z constants from DEV queries only
        A = np.concatenate([IDX[m][1] @ emb(m, q["en"])[0] for q in Q if q["split"] == "dev"]); G[m] = (float(A.mean()), float(A.std()))
    out = {"global_z_dev": G, "dev": {}, "test": {}}
    for m in ("eg2", "sig"): out["dev"][f"{m}_baseline"] = evaluate("dev", m, "baseline", G=G)
    grid = [dict(lam=l, scales=s, w=w) for l, s, w in itertools.product((0.0, 0.5, 1.0, 1.5), ((0.1, 0.2, 0.3, 0.4, 0.5), (0.2, 0.3, 0.4), (0.15, 0.25, 0.35, 0.5)), (1, 3))]
    best = {}
    for m in ("eg2", "sig", "fuse"):
        for fw in ((0.25, 0.5, 0.75) if m == "fuse" else (None,)):
            for g in grid:
                r = evaluate("dev", m, "prop", G=G, w=fw or 0.5, **g); key = (m, fw)
                sc = r["r1_5"] + r["r1_7"] + r["miou"]
                if key not in best or sc > best[key][0]: best[key] = (sc, g, r)
    for (m, fw), (sc, g, r) in best.items(): out["dev"][f"{m}{'' if fw is None else fw}_prop"] = dict(r, params=g)
    # test: baselines + every model's dev-best proposal config
    for m in ("eg2", "sig"):
        for lang in ("en", "vi"): out["test"][f"{m}_baseline_{lang}"] = evaluate("test", m, "baseline", lang=lang, G=G)
    for (m, fw), (sc, g, r) in best.items():
        for lang in ("en", "vi"): out["test"][f"{m}{'' if fw is None else fw}_prop_{lang}"] = dict(evaluate("test", m, "prop", lang=lang, G=G, w=fw or 0.5, **g), params=g)
    from vsearch.translate import Translator
    for kind in ("opus", "vinai"):
        T = Translator(kind)
        for m in ("eg2", "sig"):
            g = best[(m, None)][1]
            out["test"][f"{m}_prop_vi->{kind}"] = dict(evaluate("test", m, "prop", lang="vi", G=G, translate=T, **g), params=g)
            out["test"][f"{m}_baseline_vi->{kind}"] = evaluate("test", m, "baseline", lang="vi", G=G, translate=T)
    json.dump(out, open("results/charades_m1.json", "w"), indent=1, default=str)
    for s in ("dev", "test"):
        for k, v in out[s].items(): print(s, k.ljust(22), {x: v[x] for x in ("r1_5", "r1_7", "r5_5", "r5_7", "miou", "ms", "n")}, v.get("params", ""))
