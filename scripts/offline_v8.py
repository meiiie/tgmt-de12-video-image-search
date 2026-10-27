"""Offline v8 experiments on dumped embeddings (scripts/dump_embeddings.py / Kaggle v8 JSON).
Same segment logic + metrics as scripts/evaluate.py (1 fps keyframes, merge gap 1.5 s, tol 0.5 s, R@k, mAP@10).
Sets: large70 = all frames; small10 = frames of the 10 non-distractor videos. Query set: object_hard (58 queries).
Usage: python scripts/offline_v8.py --dump DIR --bench data/davis_bench --out results/v8_offline.json"""
import argparse, json, os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsearch.core import merge_segments
ap = argparse.ArgumentParser(); ap.add_argument("--dump", required=True); ap.add_argument("--bench", default="data/davis_bench")
ap.add_argument("--out", required=True); ap.add_argument("--timing", default="", help="json with encode ms (dump info)"); a = ap.parse_args()
L = lambda n: np.load(f"{a.dump}/{n}.npy").astype("float32") if os.path.exists(f"{a.dump}/{n}.npy") else None
FR = json.load(open(f"{a.dump}/frames.json")); NF = len(FR)
INFO = json.load(open(f"{a.dump}/info.json")) if os.path.exists(f"{a.dump}/info.json") else {}
SETS = {"large70": np.ones(NF, bool), "small10": np.array([not f["video"].startswith("distractor_") for f in FR])}
QJ = json.load(open(f"{a.bench}/queries_object_hard.json"))
nrm = lambda X: X / np.linalg.norm(X, axis=-1, keepdims=True)
D3F, D3R, EGF = L("d3_frame"), L("d3_region"), L("eg2_fp32_frame")
QD, QE = L("q_d3_object_hard"), L("q_eg2_fp32_object_hard")

def evaluate(scores_per_q, mask, tol=0.5):
    """scores_per_q: (Q, NF) frame scores (-inf = not retrieved). Returns metrics like evaluate.py."""
    R1, R5, R10, APs = [], [], [], []
    for qi, q in enumerate(QJ):
        s = scores_per_q[qi]; best = {(FR[j]["video"], FR[j]["t"]): (float(s[j]), None) for j in np.where(mask & np.isfinite(s))[0]}
        segs = merge_segments(best, 1.5)[:10]; used, rel = set(), []
        for sg in segs:
            m = next((i for i, g in enumerate(q["gt"]) if i not in used and g["video"] == sg["video"] and sg["start"] <= g["end"] + tol and sg["end"] >= g["start"] - tol), None)
            rel.append(m is not None); used.add(m)
        R1.append(any(rel[:1])); R5.append(any(rel[:5])); R10.append(any(rel[:10]))
        h = ap_ = 0
        for i, r in enumerate(rel):
            if r: h += 1; ap_ += h / (i + 1)
        APs.append(ap_ / min(len(q["gt"]), 10))
    return {"R@1": round(np.mean(R1), 3), "R@5": round(np.mean(R5), 3), "R@10": round(np.mean(R10), 3), "mAP@10": round(np.mean(APs), 3)}

def topn_trunc(vec_scores, owner, n=200):
    """emulate Searcher.search: FAISS top-n vectors per kind, frame score = max over its retrieved vectors."""
    out = np.full(NF, -np.inf); idx = np.argsort(-vec_scores)[:n]
    np.maximum.at(out, owner[idx], vec_scores[idx]); return out

def d3_scores(mask, mode="both", trunc=True):
    S = []
    nR = D3R.shape[1]; owner_r = np.repeat(np.arange(NF), nR); owner_f = np.arange(NF)
    for q in QD:
        f = D3F @ q; r = (D3R @ q).reshape(-1)
        f = np.where(mask, f, -np.inf); r = np.where(np.repeat(mask, nR), r, -np.inf)
        if trunc: s = np.maximum(topn_trunc(f, owner_f), topn_trunc(r, owner_r)) if mode == "both" else topn_trunc(f, owner_f)
        else: s = np.maximum(f, r.reshape(NF, nR).max(1)) if mode == "both" else f
        S.append(s)
    return np.array(S)

def eg_scores(mask, Q=None, X=None, dim=None, trunc=True):
    Q = QE if Q is None else Q; X = EGF if X is None else X
    if dim: Q, X = nrm(Q[:, :dim]), nrm(X[:, :dim])
    S = np.where(mask[None], Q @ X.T, -np.inf)
    return np.array([topn_trunc(s, np.arange(NF)) for s in S]) if trunc else S

def z(S, mask):
    m = S[:, mask]; mu = m.mean(1, keepdims=True); sd = m.std(1, keepdims=True) + 1e-9
    return np.where(mask[None], (S - mu) / sd, -np.inf)

def rrf(S, mask, k=60):
    R = np.full(S.shape, np.inf)
    for i, s in enumerate(S):
        o = np.argsort(-np.where(mask, s, -np.inf)); R[i, o] = np.arange(1, NF + 1)
    return np.where(mask[None], 1.0 / (k + R), -np.inf)

def gt_frames(qi, tol=0.5):
    q = QJ[qi]; return np.array([any(g["video"] == f["video"] and g["start"] - tol <= f["t"] <= g["end"] + tol for g in q["gt"]) for f in FR])

res = {"n_frames": {k: int(v.sum()) for k, v in SETS.items()}, "n_queries": len(QJ), "info": INFO}
# ---- baselines (exact evaluate.py emulation) ----
res["baseline"] = {sn: {"dinov3_both": evaluate(d3_scores(m), m), "dinov3_frame": evaluate(d3_scores(m, "frame"), m), "eg2_frame": evaluate(eg_scores(m), m)} for sn, m in SETS.items()}
print("baseline", json.dumps(res["baseline"]), flush=True)
# ---- 1. late fusion: pick w on small10 (by mAP@10, then R@1), report large70 ----
W = [round(x, 2) for x in np.arange(0, 1.0001, 0.05)]; res["fusion"] = {}
for meth in ("zscore", "rrf"):
    sweep = {}
    for sn, m in SETS.items():
        D, E = d3_scores(m, trunc=False), eg_scores(m, trunc=False)
        if meth == "zscore": D, E = z(D, m), z(E, m)
        else: D, E = rrf(D, m), rrf(E, m)
        sweep[sn] = {w: evaluate(w * E + (1 - w) * D, m) for w in W}
    wbest = max(W, key=lambda w: (sweep["small10"][w]["mAP@10"], sweep["small10"][w]["R@1"], w))
    res["fusion"][meth] = {"w_eg2_selected_on_small10": wbest, "small10": sweep["small10"][wbest], "large70": sweep["large70"][wbest],
                           "large70_oracle_best": max(sweep["large70"].items(), key=lambda kv: (kv[1]["mAP@10"], kv[1]["R@1"])),
                           "sweep": {sn: {str(w): (v["R@1"], v["mAP@10"]) for w, v in sw.items()} for sn, sw in sweep.items()}}
    print(meth, wbest, res["fusion"][meth]["small10"], res["fusion"][meth]["large70"], flush=True)
# ---- 2. two-stage: DINOv3 (frame+grid, full scores) top-K frames -> EG2 re-rank ----
res["two_stage"] = {}
for sn, m in SETS.items():
    D, E = d3_scores(m, trunc=False), eg_scores(m, trunc=False); res["two_stage"][sn] = {}
    for K in (10, 20, 50, 100, 200):
        S = np.full(D.shape, -np.inf); rec = []
        for i in range(len(QJ)):
            top = np.argsort(-D[i])[:min(K, int(m.sum()))]; S[i, top] = E[i, top]; rec.append(bool(gt_frames(i)[top].any()))
        res["two_stage"][sn][K] = {**evaluate(S, m), "stage1_recall@K": round(np.mean(rec), 3), "K_eff": min(K, int(m.sum()))}
    print("2stage", sn, res["two_stage"][sn], flush=True)
# ---- 3. EG2 Matryoshka + fp16 model + search backends ----
import faiss
res["matryoshka"] = {sn: {d: evaluate(eg_scores(m, dim=d), m) for d in (768, 512, 256, 128)} for sn, m in SETS.items()}
print("mrl", res["matryoshka"], flush=True)
import glob as _g
for tag in sorted(os.path.basename(f)[2:-16] for f in _g.glob(f"{a.dump}/q_eg2_*_object_hard.npy") if "fp32_object" not in f):
    Qx, Xx = L(f"q_{tag}_object_hard"), L(f"{tag}_frame")
    if Qx is None: continue
    res[f"{tag}"] = {sn: {"own_index": evaluate(eg_scores(m, Q=Qx, X=Xx if Xx is not None else EGF), m), "query_vs_fp32_index": evaluate(eg_scores(m, Q=Qx), m),
                      "mean_cos_to_fp32_query": round(float((nrm(Qx) * nrm(QE)).sum(1).mean()), 4)} for sn, m in SETS.items()}
    print(tag, res[tag], flush=True)
def bench(fn, n=200):
    fn(); t = time.perf_counter()
    for _ in range(n): fn()
    return round(1000 * (time.perf_counter() - t) / n, 4)
res["search_ms_box_cpu"] = {}
for d in (768, 256, 128):
    X = np.ascontiguousarray(nrm(EGF[:, :d])); q = np.ascontiguousarray(nrm(QE[:1, :d]))
    fl = faiss.IndexFlatIP(d); fl.add(X); hn = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT); hn.add(X)
    res["search_ms_box_cpu"][d] = {"numpy_matmul": bench(lambda: X @ q[0]), "faiss_flat": bench(lambda: fl.search(q, 200)), "faiss_hnsw32": bench(lambda: hn.search(q, 200)),
                                   "full_search+merge_segments": bench(lambda: merge_segments({(FR[j]["video"], FR[j]["t"]): (float(s), None) for j, s in zip(*[x[0] for x in fl.search(q, 200)][::-1])}, 1.5), 50)}
print("search", res["search_ms_box_cpu"], flush=True)
# ---- 4. SAM 3 re-rank on EG2 top-20 (crop vectors from dump; score = max(frame, best crop)) ----
SB, SE, SD = (np.load(f"{a.dump}/sam_boxes.npy") if os.path.exists(f"{a.dump}/sam_boxes.npy") else None), L("sam_eg2"), L("sam_d3")
if SB is not None and SE is not None and len(SB):
    res["sam_on_eg2"] = {}
    for sn, m in SETS.items():
        E = eg_scores(m); out = {}
        for alpha in (1.0, 0.5):
            S2 = E.copy()
            for i in range(len(QJ)):
                best = {(FR[j]["video"], FR[j]["t"]): (float(E[i, j]), None) for j in np.where(np.isfinite(E[i]))[0]}
                segs = merge_segments(best, 1.5)[:20]; key2j = {(f["video"], f["t"]): j for j, f in enumerate(FR)}
                for sg in segs:
                    j = key2j[(sg["video"], sg["peak_t"])]; rows = np.where(SB[:, 0] == j)[0]
                    if len(rows):
                        c = float((SE[rows] @ QE[i]).max()); sc = max(E[i, j], c) if alpha == 1.0 else alpha * E[i, j] + (1 - alpha) * max(E[i, j], c)
                        S2[i, j] = sc
                # non-peak frames of top-20 segments keep their score; segment score = max -> peak frame decides
            out[f"max(frame,crop)" if alpha == 1.0 else "0.5*frame+0.5*max"] = evaluate(S2, m)
        out["eg2_baseline"] = evaluate(E, m); res["sam_on_eg2"][sn] = out
    res["sam_stats"] = {"boxes": int(len(SB)), "frames_with_boxes": int(len(set(SB[:, 0].tolist()))), "boxes_per_frame": round(len(SB) / NF, 2)}
    print("sam", res["sam_on_eg2"], res["sam_stats"], flush=True)
json.dump(res, open(a.out, "w"), indent=1, default=str); print("saved", a.out)
