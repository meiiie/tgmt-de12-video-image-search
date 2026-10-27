"""Re-rank EG2 text->moment results with a d3 decision model (vLLM-SR Decision 3.0) asked yes/no per candidate.
d3-turbo (27B) does not fit the free T4 (see README), so this measures the 0.85B sibling vllm-sr/d3-lite on the box CPU.
Moment queries: EG2 window top-K segments -> d3 P(yes | peak frame, 'Does this frame show: <query>?') -> re-sort
(score = P(yes), or fused z(EG2)+z(P)). Ordinal queries: EG2 candidate segments in the loaded video -> keep those with
P(yes)>=0.5 -> n-th in time. Same hit rule as text_eval.py."""
import json, sys, time, glob, cv2, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "scripts")
from PIL import Image
from transformers import AutoModel
from vsearch.core import Embedder
from vsearch.text import TextEncoder, text_search, parse_ordinal, curves, smooth, runs
from text_eval import load, hit, tiou, err
D3 = sys.argv[1]; K = int(sys.argv[2]) if len(sys.argv) > 2 else 5
VD = {"m": "data/davis_bench/videos", "o": "data/text_eval/videos"}
def frame(vdir, v, t):
    c = cv2.VideoCapture(f"{vdir}/{v}"); c.set(cv2.CAP_PROP_POS_MSEC, t * 1000 + 1); ok, f = c.read(); c.release()
    return Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize((448, 252))
Q = json.load(open("data/text_eval/queries_text.json")); allq = Q["moment"] + Q["ordinal"]
mD, XD = load("data/text_idx/embeddinggemma-2_davis10"); mO, XO = load("data/text_idx/embeddinggemma-2_ord")
te = TextEncoder(Embedder("google/embeddinggemma-2", device="cpu"))
d3 = AutoModel.from_pretrained(D3, trust_remote_code=True).eval()
def pyes(img, text):
    r = d3.system_one(state="A frame from a video.", images=[img],
                      questions={"m": {"type": "noul", "instructions": f"Does this frame show: {text}?"}})
    return r["answers"]["m"]["noul"]
rows = {}; d3_ms = []; n_calls = 0
for q in allq:
    part = "moment" if q["id"].startswith("m_") else "ordinal"; g = q["gt"][0]
    meta, X, fps = (mD["meta"], XD, mD["fps"]) if part == "moment" else (mO["meta"], XO, mO["fps"])
    clean, n = parse_ordinal(q["text"]); e = te([clean if n else q["text"]])[0]; vdir = VD[part[0]]
    if part == "moment":
        segs = text_search(meta, X, e, fps, method="window", w=3, k=K)
        t = time.time(); P = [pyes(frame(vdir, s["video"], s["peak_t"]), q["text"]) for s in segs]; d3_ms.append((time.time() - t) * 1000); n_calls += len(segs)
        z = lambda a: (np.array(a) - np.mean(a)) / (np.std(a) + 1e-6)
        variants = {"eg2": segs, "d3_only": [segs[i] for i in np.argsort(-np.array(P), kind="stable")],
                    "eg2+d3_z": [segs[i] for i in np.argsort(-(z([s["score"] for s in segs]) + z(P)), kind="stable")]}
    else:
        t_, s_ = curves(meta, X @ e)[g["video"]]; ss = smooth(s_, 3); med, mx = np.median(ss), ss.max()
        cand = sorted(runs(t_, ss, med + 0.5 * (mx - med), 1 / fps, min_len=2), key=lambda r: r["start"]) or runs(t_, ss, mx, 1 / fps)
        for c in cand: c["video"] = g["video"]
        t = time.time(); P = [pyes(frame(vdir, c["video"], c["peak_t"]), clean) for c in cand]; d3_ms.append((time.time() - t) * 1000); n_calls += len(cand)
        pick = lambda L: [L[(n - 1) if n > 0 else n] if -len(L) <= ((n - 1) if n > 0 else n) < len(L) else L[-1]] if L else [cand[0]]
        keep = [c for c, p in zip(cand, P) if p >= 0.5]
        variants = {"eg2": pick(cand), "d3_only": pick(keep), "eg2+d3_z": pick(keep)}
    for name, segs in variants.items():
        r = rows.setdefault(name, {}).setdefault(f"{part}_{q['lang']}", {"r1": [], "r5": [], "tiou": [], "err": []})
        r["r1"].append(hit(segs[0], g)); r["r5"].append(any(hit(s, g) for s in segs[:5])); r["tiou"].append(tiou(segs[0], g) >= .5)
        if segs[0]["video"] == g["video"]: r["err"].append(err(segs[0], g))
out = {"reranker": D3, "K": K, "device": "box CPU", "d3_ms_per_query_mean": round(float(np.mean(d3_ms)), 1),
       "d3_calls": n_calls, "d3_ms_per_call": round(float(np.sum(d3_ms)) / n_calls, 1), "results": {
        v: {p: {"n": len(r["r1"]), "R@1": round(np.mean(r["r1"]), 3), "R@5": round(np.mean(r["r5"]), 3), "R@1_tIoU0.5": round(np.mean(r["tiou"]), 3),
                "mean_ts_err_s": round(float(np.mean(r["err"])), 2) if r["err"] else -1} for p, r in d.items()} for v, d in rows.items()}}
json.dump(out, open("results/text_rerank_d3-lite.json", "w"), indent=1); print(json.dumps(out, indent=1))
