"""Like build_index (frame/grid regions) but caches embeddings per video in --cache (npz+json) so a
timeout/crash keeps finished videos; re-running resumes. Output layout identical to vsearch.core.build_index."""
import argparse, glob, json, os, sys, time, numpy as np, faiss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsearch.core import Embedder, sample_frames, grid_regions, VIDEO_EXT
ap = argparse.ArgumentParser(); ap.add_argument("--videos", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--model", required=True); ap.add_argument("--cache", required=True); ap.add_argument("--regions", default="none")
ap.add_argument("--fps", type=float, default=1.0); ap.add_argument("--bs", type=int, default=16); a = ap.parse_args()
os.makedirs(a.out, exist_ok=True); os.makedirs(a.cache, exist_ok=True)
t_load = time.time(); emb = Embedder(a.model); t_load = time.time() - t_load
vids = sorted(f for f in glob.glob(os.path.join(a.videos, "*")) if f.lower().endswith(VIDEO_EXT))
emb_sec = nf_new = 0
for i, v in enumerate(vids):
    base = os.path.join(a.cache, os.path.basename(v) + f".{a.regions}")
    if os.path.exists(base + ".json"): continue
    crops, meta = [], []
    for t, img in sample_frames(v, a.fps, 0):
        crops.append(img); meta.append({"video": os.path.basename(v), "t": round(t, 3), "kind": "frame", "box": None})
        if a.regions == "grid":
            for b in grid_regions(img):
                crops.append(img.crop(b)); meta.append({"video": meta[-1]["video"], "t": round(t, 3), "kind": "region", "box": b})
    t0 = time.time(); X = emb(crops, bs=a.bs); emb_sec += time.time() - t0; nf_new += sum(m["kind"] == "frame" for m in meta)
    np.save(base + ".npy", X); json.dump(meta, open(base + ".json.tmp", "w")); os.replace(base + ".json.tmp", base + ".json")
    print(f"[{i+1}/{len(vids)}] {os.path.basename(v)} {len(meta)} vec, total emb {emb_sec:.0f}s", flush=True)
Xs, meta = [], []
for v in vids:
    base = os.path.join(a.cache, os.path.basename(v) + f".{a.regions}"); Xs.append(np.load(base + ".npy")); meta += json.load(open(base + ".json"))
X = np.concatenate(Xs).astype("float32")
for kind in ("frame", "region"):
    ids = np.array([i for i, x in enumerate(meta) if x["kind"] == kind], dtype="int64")
    if len(ids) == 0: continue
    idx = faiss.IndexIDMap(faiss.IndexFlatIP(X.shape[1])); idx.add_with_ids(X[ids], ids); faiss.write_index(idx, f"{a.out}/{kind}.faiss")
nf = sum(m["kind"] == "frame" for m in meta)
stats = {"model": a.model, "fps": a.fps, "regions": a.regions, "dedup": 0, "frames": nf, "vectors": len(meta), "load_sec": round(t_load, 1),
         "index_sec_this_run": round(emb_sec, 1), "frames_embedded_this_run": nf_new, "frames_per_sec": round(nf_new / emb_sec, 2) if emb_sec else None}
json.dump({**stats, "meta": meta}, open(f"{a.out}/meta.json", "w")); print(stats)
