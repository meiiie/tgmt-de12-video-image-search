"""Cross-domain not-found threshold for EG2 (window cosine of the best segment, the app's rule).
Calibrate on DAVIS moment (60 pos / 30 neg, all 10 videos) + Charades DEV (53 pos, each in its own video; negatives =
the DAVIS negative list minus indoor-plausible ones, asked against the same dev videos). Report on held-out football
(16 pos / 28 neg) and Charades TEST (97 pos / neg likewise)."""
import json, sys, numpy as np
sys.path.insert(0, ".")
from vsearch.core import Searcher
NEG = json.load(open("eval_text/negatives.json"))["queries"]
INDOOR = ("cooking", "nấu ăn", "laptop", "máy tính", "piano", "đàn", "cat ", "mèo", "cake", "bánh")  # could occur in Charades homes
NEG_OUT = [q for q in NEG if not any(w in q["text"] for w in INDOOR)]
NEG_FB = [q for q in NEG if "football" not in q["text"] and "bóng đá" not in q["text"]]
CQ = json.load(open("eval_charades/queries.json"))["queries"]
def best(S, text, video=None): return S.search_text(text, 1, video=video)[0]["score"]
D = Searcher("data/text_idx/embeddinggemma-2_davis10"); C = Searcher("data/text_idx/embeddinggemma-2_charades", embedder=D.emb); F = Searcher("data/text_idx/embeddinggemma-2_soccer", embedder=D.emb)
Qt = json.load(open("eval_text/queries_text.json"))["moment"]; SOC = json.load(open("eval_text/soccer_queries.json"))["queries"]
pos_cal = [best(D, q["text"]) for q in Qt] + [best(C, q[l], q["video"]) for q in CQ if q["split"] == "dev" for l in ("en", "vi")]
neg_cal = [best(D, q["text"]) for q in NEG] + [best(C, q["text"], v) for q in NEG_OUT for v in sorted({x["video"] for x in CQ if x["split"] == "dev"})[:10]]
pos_fb = [best(F, q["text"]) for q in SOC]; neg_fb = [best(F, q["text"]) for q in NEG_FB]
tv = sorted({x["video"] for x in CQ if x["split"] == "test"})[:10]
pos_ct = [best(C, q[l], q["video"]) for q in CQ if q["split"] == "test" for l in ("en", "vi")]; neg_ct = [best(C, q["text"], v) for q in NEG_OUT for v in tv]
P, N = np.array(pos_cal), np.array(neg_cal)
def f1(t): tp = (P >= t).sum(); fp = (N >= t).sum(); p = tp / max(1, tp + fp); r = tp / len(P); return 2 * p * r / max(1e-9, p + r)
cands = np.unique(np.concatenate([P, N])); tau = float(max(cands, key=lambda t: (f1(t), -t)))
tau_fa5 = float(min(t for t in cands if (N >= t).mean() <= 0.05))
rep = {"n": {"cal_pos": len(P), "cal_neg": len(N), "fb_pos": len(pos_fb), "fb_neg": len(neg_fb), "ct_pos": len(pos_ct), "ct_neg": len(neg_ct)}}
for nm, t in (("old_davis_only", 0.637), ("maxF1", tau), ("FAR<=5%", tau_fa5)):
    m = lambda p, n: {"FAR": round(float((np.array(n) >= t).mean()), 3), "FRR": round(float((np.array(p) < t).mean()), 3)}
    rep[nm] = {"tau": round(t, 4), "calibration": m(P, N), "football": m(pos_fb, neg_fb), "charades_test": m(pos_ct, neg_ct)}
    print(nm, rep[nm])
json.dump(rep, open("results/threshold_crossdomain.json", "w"), indent=1)
