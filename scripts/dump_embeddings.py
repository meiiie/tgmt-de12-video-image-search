"""v8 (GPU): dump every embedding needed for offline experiments (fusion, two-stage, Matryoshka, FAISS, SAM re-rank on EG2)
into one npz: DINOv3 frame+grid vectors, EG2 frame vectors (fp32 and fp16 model), SAM 3 masked-crop vectors (EG2 + DINOv3),
query vectors for both query sets, and per-query timing (encode vs search). Frames = 1 fps over data/davis_bench_large
(70 videos; the 10 val videos are the 10-video set)."""
import argparse, glob, json, os, sys, time, numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
from vsearch.core import Embedder, sample_frames, grid_regions, VIDEO_EXT
ap = argparse.ArgumentParser(); ap.add_argument("--bench", default="data/davis_bench_large"); ap.add_argument("--dino", required=True)
ap.add_argument("--eg2", required=True); ap.add_argument("--out", required=True); ap.add_argument("--stage", required=True)
ap.add_argument("--budget", type=float, default=1e9); a = ap.parse_args(); T0 = time.time()
os.makedirs(a.out, exist_ok=True); info_p = f"{a.out}/info.json"; info = json.load(open(info_p)) if os.path.exists(info_p) else {}
def save_info(): json.dump(info, open(info_p, "w"), indent=1)
sync = (lambda: torch.cuda.synchronize()) if torch.cuda.is_available() else (lambda: None)
vids = sorted(f for f in glob.glob(f"{a.bench}/videos/*") if f.lower().endswith(VIDEO_EXT))
def frames():
    for v in vids:
        for t, im in sample_frames(v, 1.0, 0): yield os.path.basename(v), round(t, 3), im
QS = {q: json.load(open(f"{a.bench}/queries_{q}.json")) for q in ("object_hard", "object")}
def qimgs(q): return [Image.open(os.path.join(a.bench, x["image"])).convert("RGB") for x in QS[q]]
def timed_queries(E, name):
    out = {}
    for q in QS:
        ims = qimgs(q); E(ims[:2]); vs, ts = [], []
        for im in ims:
            sync(); t = time.time(); vs.append(E([im])); sync(); ts.append(time.time() - t)
        np.save(f"{a.out}/q_{name}_{q}.npy", np.concatenate(vs).astype("float16" if False else "float32"))
        out[q] = {"encode_ms_mean": round(1000*np.mean(ts), 1), "encode_ms_p50": round(1000*np.median(ts), 1)}
        print(name, q, out[q], flush=True)
    return out
if a.stage == "dino":
    E = Embedder(a.dino); meta, F, R = [], [], []
    for v, t, im in frames():
        crops = [im] + [im.crop(b) for b in grid_regions(im)]; X = E(crops); F.append(X[:1]); R.append(X[1:]); meta.append({"video": v, "t": t})
    np.save(f"{a.out}/d3_frame.npy", np.concatenate(F).astype("float16")); np.save(f"{a.out}/d3_region.npy", np.stack(R).astype("float16"))
    json.dump(meta, open(f"{a.out}/frames.json", "w")); info["dino_q"] = timed_queries(E, "d3"); info["n_frames"] = len(meta); save_info()
elif a.stage.startswith("eg2"):  # eg2_fp32 / eg2_fp16 / eg2_bf16_tok70 (tokN = image soft-token budget, default 280)
    parts = a.stage.split("_"); dt = parts[1]; os.environ["DE12_EG2_DTYPE"] = dt
    t = time.time(); E = Embedder(a.eg2); info[f"{a.stage}_load_s"] = round(time.time() - t, 1)
    if len(parts) > 2:
        n = int(parts[2][3:]); p = E.m[0].processor; p.image_processor.max_soft_tokens = n; p.image_processor.image_seq_length = n; p.image_seq_length = n; dt = dt + parts[2]
    ims = [im for _, _, im in frames()]; sync(); t = time.time(); X = E(ims, bs=16); sync()
    info[f"{a.stage}_index_fps"] = round(len(ims) / (time.time() - t), 2); info[f"{a.stage}_nan"] = int(np.isnan(X).sum())
    np.save(f"{a.out}/eg2_{dt}_frame.npy", X.astype("float16")); info[f"{a.stage}_q"] = timed_queries(E, f"eg2_{dt}")
    # encode split: image preprocessing (CPU, processor) vs model forward; via ST module 0 processor if exposed
    try:
        im = qimgs("object_hard")[0].resize((224, 224)); m = E.m; feats = None; ts_pre, ts_fwd = [], []
        for _ in range(10):
            sync(); t = time.time(); feats = m.preprocess([{"image": im}]) if hasattr(m, "preprocess") else m.tokenize([{"image": im}]); ts_pre.append(time.time() - t)
            feats = {k: (v.to(m.device) if hasattr(v, "to") else v) for k, v in feats.items()}
            sync(); t = time.time()
            with torch.inference_mode(): m.forward(feats)
            sync(); ts_fwd.append(time.time() - t)
        info[f"{a.stage}_split_ms"] = {"preprocess": round(1000*np.median(ts_pre), 1), "forward": round(1000*np.median(ts_fwd), 1)}
    except Exception as e: info[f"{a.stage}_split_err"] = repr(e)[:300]
    save_info()
elif a.stage == "sam":
    from vsearch.sam3_regions import SAM3Regions, masked_crop
    S = SAM3Regions(); info["sam_load"] = S.load_info; boxes, crops, ts = [], [], []
    for i, (v, t, im) in enumerate(frames()):
        if time.time() - T0 > a.budget: info["sam_truncated_at_frame"] = i; break
        sync(); t0 = time.time(); bs = S(im); sync(); ts.append(time.time() - t0)
        for b, mk in zip(bs, S.last_masks): boxes.append([i, *b]); crops.append(masked_crop(im, b, mk))
    info["sam_s_per_frame"] = round(float(np.mean(ts)), 3); info["sam_boxes"] = len(boxes); info["sam_frames"] = len(ts)
    np.save(f"{a.out}/sam_boxes.npy", np.array(boxes, dtype="int32").reshape(-1, 5)); save_info()
    del S; torch.cuda.empty_cache()
    import pickle; pickle.dump(crops, open("/tmp/sam_crops.pkl", "wb"))
elif a.stage.startswith("samemb_"):
    import pickle; crops = pickle.load(open("/tmp/sam_crops.pkl", "rb"))
    for name, path in [x for x in (("d3", a.dino), ("eg2", a.eg2)) if x[0] == a.stage[7:]]:
        os.environ["DE12_EG2_DTYPE"] = "fp32"; E = Embedder(path); t = time.time()
        X = E(crops, bs=16) if crops else np.zeros((0, 768), "float32"); info[f"sam_crop_{name}_s"] = round(time.time() - t, 1)
        np.save(f"{a.out}/sam_{name}.npy", X.astype("float16")); del E; torch.cuda.empty_cache(); save_info()
print(a.stage, "done", round(time.time() - T0, 1), "s")
