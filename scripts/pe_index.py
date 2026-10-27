"""Build a frame-only index (same format as build_index) with Perception Encoder. Usage: python scripts/pe_index.py VIDEO_DIR OUT_DIR [hf-id]"""
import sys, os, glob, json, time, numpy as np, faiss
sys.path.insert(0, ".")
from vsearch.core import sample_frames, VIDEO_EXT
from vsearch.pe import PEEmbedder
vd, out = sys.argv[1], sys.argv[2]; name = sys.argv[3] if len(sys.argv) > 3 else "timm/PE-Core-B-16"
os.makedirs(out, exist_ok=True); e = PEEmbedder(name); vecs, meta, t0 = [], [], time.time()
for v in sorted(f for f in glob.glob(os.path.join(vd, "*")) if f.lower().endswith(VIDEO_EXT)):
    for t, img in sample_frames(v, 1.0, 0):
        vecs.append(e([img])); meta.append({"video": os.path.basename(v), "t": round(t, 3), "kind": "frame", "box": None})
X = np.concatenate(vecs); dt = time.time() - t0
idx = faiss.IndexIDMap(faiss.IndexFlatIP(X.shape[1])); idx.add_with_ids(X, np.arange(len(X), dtype="int64")); faiss.write_index(idx, f"{out}/frame.faiss")
json.dump({"model": name, "fps": 1.0, "regions": "none", "dedup": 0, "frames": len(X), "vectors": len(X), "index_sec": round(dt, 1), "frames_per_sec": round(len(X)/dt, 2), "meta": meta}, open(f"{out}/meta.json", "w"))
print("PEDONE", len(X), round(dt, 1))
