"""Evaluate text->moment search. Usage: python scripts/text_eval.py <model> [--translate]
Hit rule (stated in README): a returned segment is a hit if it is in the GT video AND its peak time lies inside the
GT span widened by TOL=0.5 s on each side. R@1/R@5 over ranked segments. Also tIoU>=0.5 R@1 on [start,end].
Timestamp error = |peak_t - nearest point of GT span| of the top-1 result (0 if inside), only when the video is right.
Moment queries search all 10 DAVIS-bench videos; ordinal queries are scoped to their composite video (user loaded it)."""
import json, sys, time, faiss, numpy as np
sys.path.insert(0, ".")
from vsearch.core import Embedder
from vsearch.text import TextEncoder, text_search, parse_ordinal
TOL = 0.5
def load(d):
    m = json.load(open(f"{d}/meta.json")); ix = faiss.read_index(f"{d}/frame.faiss")
    inner = faiss.downcast_index(ix.index); ids = faiss.vector_to_array(ix.id_map)
    X = np.zeros((len(m["meta"]), inner.d), "float32"); X[ids] = inner.reconstruct_n(0, inner.ntotal); return m, X
def hit(s, g): return s["video"] == g["video"] and g["start"] - TOL <= s["peak_t"] <= g["end"] + TOL
def tiou(s, g):
    if s["video"] != g["video"]: return 0.0
    i = max(0, min(s["end"], g["end"]) - max(s["start"], g["start"])); u = max(s["end"], g["end"]) - min(s["start"], g["start"])
    return i / u if u > 0 else 0
def err(s, g): return max(0.0, g["start"] - s["peak_t"], s["peak_t"] - g["end"])
def run(model, translate=False, configs=None):
    tag = model.split("/")[-1]; Q = json.load(open("data/text_eval/queries_text.json"))
    mD, XD = load(f"data/text_idx/{tag}_davis10"); mO, XO = load(f"data/text_idx/{tag}_ord")
    emb = Embedder(model, device="cpu"); te = TextEncoder(emb, translate="opus" if translate else None)
    res = {}
    allq = Q["moment"] + Q["ordinal"]
    # encode: raw text, and ordinal-stripped text (for the ordinal-aware method)
    t0 = time.time(); Eraw = np.concatenate([te([q["text"]]) for q in allq]); enc_ms = (time.time() - t0) / len(allq) * 1000
    Ecl = np.concatenate([te([parse_ordinal(q["text"])[0]]) for q in allq])
    for name, cfg in (configs or {"frame": dict(method="frame"), "window_w3": dict(method="window", w=3), "window_w5": dict(method="window", w=5)}).items():
        for use_ord in (False, True):
            key = f"{name}{'+ordinal' if use_ord else ''}"; rows = {}
            for i, q in enumerate(allq):
                part = "moment" if q["id"].startswith("m_") else "ordinal"
                meta, X, fps = (mD["meta"], XD, mD["fps"]) if part == "moment" else (mO["meta"], XO, mO["fps"])
                n = parse_ordinal(q["text"])[1] if use_ord else None
                t1 = time.time()
                segs = text_search(meta, X, (Ecl if use_ord and n else Eraw)[i], fps, ordinal=n,
                                   video=q["gt"][0]["video"] if part == "ordinal" else None, k=5, **cfg)
                sm = (time.time() - t1) * 1000; g = q["gt"][0]
                r = rows.setdefault(f"{part}_{q['lang']}", {"r1": [], "r5": [], "tiou1": [], "err": [], "search_ms": []})
                r["r1"].append(hit(segs[0], g)); r["r5"].append(any(hit(s, g) for s in segs[:5]))
                r["tiou1"].append(tiou(segs[0], g) >= 0.5); r["search_ms"].append(sm)
                if segs[0]["video"] == g["video"]: r["err"].append(err(segs[0], g))
            res[key] = {p: {"n": len(r["r1"]), "R@1": round(np.mean(r["r1"]), 3), "R@5": round(np.mean(r["r5"]), 3),
                            "R@1_tIoU0.5": round(np.mean(r["tiou1"]), 3), "mean_ts_err_s": round(float(np.mean(r["err"])) if r["err"] else -1, 2),
                            "search_ms": round(float(np.mean(r["search_ms"])), 2)} for p, r in rows.items()}
    out = {"model": model, "translate_vi_en": translate, "tol_s": TOL, "text_encode_ms_per_query_cpu": round(enc_ms, 1),
           "index_fps": mD["fps"], "frames": {"davis10": mD["frames"], "ord": mO["frames"]},
           "index_sec_cpu": {"davis10": mD["index_sec"], "ord": mO["index_sec"]}, "results": res}
    return out
if __name__ == "__main__":
    m = sys.argv[1]; tr = "--translate" in sys.argv
    o = run(m, tr); f = f"results/text_{m.split('/')[-1]}{'_opusmt' if tr else ''}.json"
    json.dump(o, open(f, "w"), indent=1); print(json.dumps(o, indent=1)); print("->", f)
