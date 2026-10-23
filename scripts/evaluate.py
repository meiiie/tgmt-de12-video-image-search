"""queries.json: [{"image": path, "gt": [{"video","start","end"}]}]. Ranked list = merged segments.
A segment is relevant if it overlaps a GT interval (+/- tol) not yet matched (each GT matched once).
Reports Recall@{1,5,10} (any relevant in top-K), mAP@10, mean search latency."""
import argparse, json, sys, os, time, numpy as np; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image; from vsearch.core import Searcher
ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True); ap.add_argument("--queries", required=True)
ap.add_argument("--modes", default="frame,region,both"); ap.add_argument("--tol", type=float, default=0.5); ap.add_argument("--out"); ap.add_argument("--max_area", type=float, default=1.0, help="only object queries with mask area fraction < this"); a = ap.parse_args()
Q = [q for q in json.load(open(a.queries)) if q.get("area_frac", 0) < a.max_area]; S = Searcher(a.index); base = os.path.dirname(os.path.abspath(a.queries)); res = {}
QV, QT = [], []
for q in Q:
    img = Image.open(os.path.join(base, q["image"])).convert("RGB"); t = time.time(); QV.append(S.emb([img])); QT.append(time.time() - t)
for mode in a.modes.split(","):
    R = {1: [], 5: [], 10: []}; APs = []; lat = []; PK = []
    for qi, q in enumerate(Q):
        t = time.time(); segs = S.search(None, mode, 10, qvec=QV[qi]); lat.append(QT[qi] + time.time() - t)
        used, rel = set(), []
        for s in segs:
            m = next((i for i, g in enumerate(q["gt"]) if i not in used and g["video"] == s["video"] and s["start"] <= g["end"] + a.tol and s["end"] >= g["start"] - a.tol), None)
            rel.append(m is not None); used.add(m)
        for k in R: R[k].append(float(any(rel[:k])))
        top = segs[0]; PK.append(float(any(g["video"] == top["video"] and g["start"] <= top["peak_t"] <= g["end"] for g in q["gt"])))
        hits = 0; ap_ = 0.0
        for i, r in enumerate(rel):
            if r: hits += 1; ap_ += hits / (i + 1)
        APs.append(ap_ / min(len(q["gt"]), 10))
    res[mode] = {**{f"R@{k}": round(float(np.mean(v)), 3) for k, v in R.items()}, "mAP@10": round(float(np.mean(APs)), 3), "top1_peak_in_GT": round(float(np.mean(PK)), 3), "ms/query": round(1000*float(np.mean(lat)), 1), "n_queries": len(Q)}
    print(mode, res[mode])
if a.out: json.dump({"index": S.d | {"meta": None}, "results": res}, open(a.out, "w"), indent=1)
