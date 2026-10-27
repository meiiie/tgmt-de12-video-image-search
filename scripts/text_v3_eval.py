"""Text search v3: order-word events v2 + EG2/SigLIP 2 score fusion + not-found threshold.
All parameters are selected on DAVIS only (60 moment + 32 ordinal queries; 30 negatives), then reported on football.
Fusion: z-score with GLOBAL per-model constants (mean/std of all frame scores over the DAVIS moment queries), so the fused
score stays absolute and can be thresholded; s = w*zEG2 + (1-w)*zSigLIP2. RRF (k=60, per query ranks) for comparison."""
import json, sys, time, itertools, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from vsearch.core import Embedder
from vsearch.text import TextEncoder, text_search, parse_ordinal
from text_eval import load, err
TOL = 0.5; M = {"eg2": "embeddinggemma-2", "sig": "siglip2-base-patch16-224"}
def hit(s, gts): return any(s["video"] == g["video"] and g["start"] - TOL <= s["peak_t"] <= g["end"] + TOL for g in gts)
Qt = json.load(open("eval_text/queries_text.json")); NEG = json.load(open("eval_text/negatives.json"))["queries"]
SOC = json.load(open("eval_text/soccer_queries.json"))["queries"]
SETS = {"davis_moment": ("davis10", [dict(q, scope=None) for q in Qt["moment"]]),
        "davis_ordinal": ("ord", [dict(q, scope=q["gt"][0]["video"]) for q in Qt["ordinal"]]),
        "football": ("soccer", [dict(q, scope=None) for q in SOC]),
        "neg_davis": ("davis10", [dict(q, scope=None, gt=[]) for q in NEG]),
        "neg_football": ("soccer", [dict(q, scope=None, gt=[]) for q in NEG if "football" not in q["text"] and "bóng đá" not in q["text"]])}
IDX = {(m, s): load(f"data/text_idx/{M[m]}_{s}") for m in M for s in ("davis10", "ord", "soccer")}
# encode every query once per model (clean = order words removed); time it
texts = sorted({q["text"] for _, qs in SETS.values() for q in qs} | {parse_ordinal(q["text"])[0] for _, qs in SETS.values() for q in qs})
E, ENC_MS = {}, {}
for m, name in (("eg2", "google/embeddinggemma-2"), ("sig", "google/siglip2-base-patch16-224")):
    te = TextEncoder(Embedder(name, device="cpu")); te(["warm up"]); t = time.time()
    V = np.concatenate([te([x]) for x in texts]); ENC_MS[m] = (time.time() - t) / len(texts) * 1000; E[m] = dict(zip(texts, V))
# global z constants from DAVIS moment queries
G = {}
for m in M:
    X = IDX[(m, "davis10")][1]; A = np.concatenate([X @ E[m][q["text"]] for q in SETS["davis_moment"][1]]); G[m] = (float(A.mean()), float(A.std()))
def frame_scores(q_text, s, w, fusion):
    sE = IDX[("eg2", s)][1] @ E["eg2"][q_text]; sS = IDX[("sig", s)][1] @ E["sig"][q_text]
    if fusion == "rrf":
        r = lambda a: np.argsort(np.argsort(-a)); return w / (60 + r(sE)) + (1 - w) / (60 + r(sS))
    return w * (sE - G["eg2"][0]) / G["eg2"][1] + (1 - w) * (sS - G["sig"][0]) / G["sig"][1]
def run(q, s, w, fusion, ordm):
    meta, fps = IDX[("eg2", s)][0]["meta"], IDX[("eg2", s)][0]["fps"]; Xd = IDX[("eg2", s)][1]
    clean, n = parse_ordinal(q["text"]) if ordm else (q["text"], None)
    sc = frame_scores(clean if n else q["text"], s, w, fusion)
    best = text_search(meta, None, None, fps, scores=sc, video=q["scope"], k=5)
    if n:
        kw = dict(ordinal=n, video=q["scope"] or best[0]["video"], k=5, scores=sc)
        segs = text_search(meta, None, None, fps, **kw) if ordm == "v1" else text_search(meta, None, None, fps, ord_v2=ordm, Xdup=Xd, **kw)
    else: segs = best
    return best[0]["score"], segs
def evaluate(setname, w, fusion, ordm):
    s, qs = SETS[setname]; rows = []
    for q in qs:
        sc, segs = run(q, s, w, fusion, ordm)
        rows.append({"id": q["id"], "lang": q["lang"], "score": sc, "h1": hit(segs[0], q["gt"]) if q["gt"] else False,
                     "h5": any(hit(x, q["gt"]) for x in segs[:5]) if q["gt"] else False,
                     "err": min(err(segs[0], g) for g in q["gt"]) if q["gt"] else None, "peak": segs[0]["peak_t"], "text": q["text"]})
    return rows
def summ(rows):
    out = {}
    for lang in ("all", "en", "vi"):
        r = [x for x in rows if lang == "all" or x["lang"] == lang]
        out[lang] = {"n": len(r), "R@1": round(float(np.mean([x["h1"] for x in r])), 3), "R@5": round(float(np.mean([x["h5"] for x in r])), 3),
                     "ts_err_s": round(float(np.mean([x["err"] for x in r if x["err"] is not None])), 2)}
    return out
# ---- selection on DAVIS ----
V1 = "v1"; grid_ord = [V1] + [dict(rho=r, gap=g, dup=None) for r, g in itertools.product((0.1, 0.2, 0.3, 0.4, 0.5), (1.0, 2.0, 3.0))]
cfgs = [("eg2", 1.0, "z"), ("sig", 0.0, "z")] + [("fuse_z", w, "z") for w in (0.25, 0.5, 0.75)] + [("fuse_rrf", w, "rrf") for w in (0.25, 0.5, 0.75)]
sel = []
for name, w, fu in cfgs:
    mom = np.mean([x["h1"] for x in evaluate("davis_moment", w, fu, None)])
    for o in grid_ord:
        od = np.mean([x["h1"] for x in evaluate("davis_ordinal", w, fu, o)])
        sel.append({"model": name, "w": w, "fusion": fu, "ord": o, "davis_moment_R1": round(float(mom), 3), "davis_ord_R1": round(float(od), 3),
                    "davis_all_R1": round(float((mom * 60 + od * 32) / 92), 3)})
# best ordinal params per model (DAVIS), ties -> v1 first, then larger rho, smaller gap (order in grid)
best = {}
for r in sel:
    k = (r["model"], r["w"]); 
    if k not in best or r["davis_all_R1"] > best[k]["davis_all_R1"]: best[k] = r
winner = max(best.values(), key=lambda r: r["davis_all_R1"])
DUP = 0.9  # replay filter: cannot be tuned on DAVIS (no replays there); fixed a priori, reported with and without
report = {"enc_ms_cpu": {k: round(v, 1) for k, v in ENC_MS.items()}, "global_z": G, "selection_grid": sel,
          "best_per_model": list(best.values()), "winner_on_davis": winner, "dup": DUP, "detail": {}}
for (name, w), b in best.items():
    o = b["ord"]; o2 = dict(o, dup=DUP) if isinstance(o, dict) else o
    d = {"ord_params": o}
    d["davis_moment"] = summ(evaluate("davis_moment", w, b["fusion"], None)); d["davis_ordinal"] = summ(evaluate("davis_ordinal", w, b["fusion"], o))
    d["davis_ordinal_v1"] = summ(evaluate("davis_ordinal", w, b["fusion"], "v1"))
    fr = evaluate("football", w, b["fusion"], o); d["football"] = summ(fr)
    d["football_v1"] = summ(evaluate("football", w, b["fusion"], "v1"))
    if isinstance(o, dict):
        d["davis_ordinal_dup"] = summ(evaluate("davis_ordinal", w, b["fusion"], o2)); fr2 = evaluate("football", w, b["fusion"], o2); d["football_dup"] = summ(fr2)
        d["football_dup_rows"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for x in fr2]
    d["football_rows"] = [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for x in fr]
    if b["fusion"] == "z":  # not-found threshold on DAVIS (moment positives vs negatives), applied to football
        ps = np.array([x["score"] for x in evaluate("davis_moment", w, "z", None)]); ph = np.array([x["h1"] for x in evaluate("davis_moment", w, "z", None)])
        ns = np.array([x["score"] for x in evaluate("neg_davis", w, "z", None)])
        cands = np.unique(np.concatenate([ps, ns]))
        def f1(t):
            tp = (ps >= t).sum(); fp = (ns >= t).sum(); p = tp / max(1, tp + fp); r = tp / len(ps); return 2 * p * r / max(1e-9, p + r)
        tau = float(max(cands, key=lambda t: (f1(t), t))); tau_mid = float((ps.min() + ns.max()) / 2) if ps.min() > ns.max() else tau
        fsc = np.array([x["score"] for x in fr]); fh = np.array([x["h1"] for x in fr]); fn = np.array([x["score"] for x in evaluate("neg_football", w, "z", None)])
        T = {}
        for nm, t in (("tau_maxF1", tau), ("tau_midgap", tau_mid)):
            T[nm] = {"tau": round(t, 4), "davis_FAR": round(float((ns >= t).mean()), 3), "davis_FRR": round(float((ps < t).mean()), 3),
                     "davis_R1_after": round(float(((ps >= t) & ph).mean()), 3), "football_FAR": round(float((fn >= t).mean()), 3),
                     "football_FRR": round(float((fsc < t).mean()), 3), "football_R1_after": round(float(((fsc >= t) & fh).mean()), 3)}
        d["threshold"] = dict(T, davis_pos_min=round(float(ps.min()), 4), davis_neg_max=round(float(ns.max()), 4), n_neg_davis=len(ns), n_neg_football=len(fn))
    report["detail"][f"{name}_w{w}"] = d
json.dump(report, open("results/text_v3.json", "w"), indent=1, ensure_ascii=False, default=str)
print("winner", winner); print("enc", report["enc_ms_cpu"])
for k, d in report["detail"].items():
    print(k, d["ord_params"], "| Dm", d["davis_moment"]["all"]["R@1"], d["davis_moment"]["vi"]["R@1"], "| Do", d["davis_ordinal"]["all"]["R@1"], "(v1", d["davis_ordinal_v1"]["all"]["R@1"], ")",
          "| F", d["football"]["all"]["R@1"], d["football"]["en"]["R@1"], d["football"]["vi"]["R@1"], "err", d["football"]["all"]["ts_err_s"], "(v1", d["football_v1"]["all"]["R@1"], ")",
          "| Fdup", d.get("football_dup", {}).get("all", {}).get("R@1"), "| thr", d.get("threshold", {}).get("tau_maxF1"))
