"""(1) 'not found' threshold for text search, (2) football demo (match.mp4). Usage: python scripts/text_extra_eval.py <model>
Threshold score = window-smoothed cosine of the best segment (ordinal words stripped). Calibrated ONLY on DAVIS-bench:
60 moment queries (present) vs 30 negatives (absent). tau_F1 = max F1 of 'present'; tau_FAR10 = lowest tau with
false-accept rate <= 10%. Then applied unchanged to the football video (16 queries vs 28 negatives)."""
import json, sys, time, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from vsearch.core import Embedder
from vsearch.text import TextEncoder, text_search, parse_ordinal
from text_eval import load, err
TOL = 0.5
def hit(s, gts): return any(s["video"] == g["video"] and g["start"] - TOL <= s["peak_t"] <= g["end"] + TOL for g in gts)
model = sys.argv[1]; tag = model.split("/")[-1]
te = TextEncoder(Embedder(model, device="cpu"))
Qm = json.load(open("eval_text/queries_text.json"))["moment"]; N = json.load(open("eval_text/negatives.json"))["queries"]
S = json.load(open("eval_text/soccer_queries.json"))["queries"]
mD, XD = load(f"data/text_idx/{tag}_davis10"); mS, XS = load(f"data/text_idx/{tag}_soccer")
def run(q, meta, X, fps):
    clean, n = parse_ordinal(q); t = time.time(); e = te([clean])[0]; enc = time.time() - t
    best = text_search(meta, X, e, fps, k=5)
    segs = text_search(meta, X, e, fps, ordinal=n, video=best[0]["video"], k=5) if n else best
    return best[0]["score"], segs, (time.time() - t) * 1000, enc * 1000
pos = [run(q["text"], mD["meta"], XD, mD["fps"]) + (hit(run(q["text"], mD["meta"], XD, mD["fps"])[1][0], q["gt"]),) for q in Qm]
neg = [run(q["text"], mD["meta"], XD, mD["fps"])[0] for q in N]
ps = np.array([p[0] for p in pos]); ph = np.array([p[4] for p in pos]); ns = np.array(neg)
def at(tau, ps, ph, ns):
    acc = ps >= tau; tp = (acc & ph).sum()  # accepted AND correct
    far = float((ns >= tau).mean()); frr = float((~acc).mean())
    prec = (acc.sum()) / max(1, acc.sum() + (ns >= tau).sum()); rec = acc.mean(); f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {"tau": round(float(tau), 4), "false_accept_rate": round(far, 3), "false_reject_rate": round(frr, 3), "F1_present": round(float(f1), 3),
            "R@1_no_threshold": round(float(ph.mean()), 3), "R@1_with_threshold": round(float(tp / len(ph)), 3)}
cands = np.unique(np.concatenate([ps, ns]))
tF1 = max(cands, key=lambda t: (at(t, ps, ph, ns)["F1_present"], t))
tFA = min([t for t in cands if at(t, ps, ph, ns)["false_accept_rate"] <= 0.10])
out = {"model": model, "calibration_davis": {"n_pos": len(ps), "n_neg": len(ns), "pos_score_mean": round(float(ps.mean()), 4), "neg_score_mean": round(float(ns.mean()), 4),
       "pos_min": round(float(ps.min()), 4), "neg_max": round(float(ns.max()), 4), "tau_F1": at(tF1, ps, ph, ns), "tau_FAR10": at(tFA, ps, ph, ns)}}
# football
rows = []; 
for q in S:
    sc, segs, ms, enc = run(q["text"], mS["meta"], XS, mS["fps"])
    rows.append({"id": q["id"], "text": q["text"], "score": round(sc, 4), "top1": {k: round(segs[0][k], 2) for k in ("start", "end", "peak_t")},
                 "hit@1": hit(segs[0], q["gt"]), "hit@5": any(hit(s, q["gt"]) for s in segs[:5]),
                 "ts_err_s": round(min(err(segs[0], g) for g in q["gt"]), 2), "latency_ms": round(ms, 1), "encode_ms": round(enc, 1)})
nS = np.array([run(q["text"], mS["meta"], XS, mS["fps"])[0] for q in N if "football" not in q["text"] and "bóng đá" not in q["text"]])
sS = np.array([r["score"] for r in rows]); hS = np.array([r["hit@1"] for r in rows])
out["football"] = {"n": len(rows), "R@1": round(float(hS.mean()), 3), "R@5": round(float(np.mean([r["hit@5"] for r in rows])), 3),
                   "mean_ts_err_s": round(float(np.mean([r["ts_err_s"] for r in rows])), 2), "latency_ms_mean": round(float(np.mean([r["latency_ms"] for r in rows])), 1),
                   "n_neg": len(nS), "at_tau_F1": at(tF1, sS, hS, nS), "at_tau_FAR10": at(tFA, sS, hS, nS), "queries": rows}
json.dump(out, open(f"results/text_extra_{tag}.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != "football"}, indent=1)); f = dict(out["football"]); qs = f.pop("queries"); print(json.dumps(f, indent=1))
for r in qs: print(r["hit@1"], r["score"], r["top1"], r["ts_err_s"], r["latency_ms"], r["text"])
