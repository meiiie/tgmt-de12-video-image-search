"""Video image/object search: frames -> (full-frame + region) embeddings -> FAISS -> segments."""
import json, os, glob, time
import cv2, numpy as np, faiss, torch
from PIL import Image
from transformers import AutoModel, AutoProcessor, AutoImageProcessor

VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv", ".webm")

# ---------------- frames ----------------
def ahash(fr):
    g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (8, 8), interpolation=cv2.INTER_AREA)
    return (g > g.mean()).flatten()

def sample_frames(path, fps=1.0, dedup=0):
    """Uniform sampling. dedup>0: skip a frame whose 64-bit aHash is within `dedup` bits of the last kept frame
    (idea borrowed from DigUp). Yields (t_sec, PIL.Image)."""
    last = None
    cap = cv2.VideoCapture(path); vfps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step, i = max(1, round(vfps / fps)), 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        if i % step == 0:
            h = ahash(fr) if dedup else None
            if dedup and last is not None and int((h != last).sum()) <= dedup:
                i += 1; continue
            last = h
            yield i / vfps, Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        i += 1
    cap.release()

# ---------------- regions ----------------
def grid_regions(img, levels=(2, 3), overlap=0.25):
    """Detector-free region proposals: overlapping multi-scale grid. Returns list of (x0,y0,x1,y1)."""
    W, H = img.size; boxes = []
    for n in levels:
        cw, ch = W / n, H / n; pw, ph = cw * overlap, ch * overlap
        for r in range(n):
            for c in range(n):
                boxes.append((max(0, int(c*cw-pw)), max(0, int(r*ch-ph)), min(W, int((c+1)*cw+pw)), min(H, int((r+1)*ch+ph))))
    return boxes

class OWLv2Regions:
    """Optional open-vocab/objectness proposals (GPU recommended). google/owlv2-base-patch16-ensemble."""
    def __init__(self, name="google/owlv2-base-patch16-ensemble", topk=8, device="cpu"):
        from transformers import Owlv2Processor, Owlv2ForObjectDetection
        self.p = Owlv2Processor.from_pretrained(name); self.m = Owlv2ForObjectDetection.from_pretrained(name).to(device).eval()
        self.k, self.dev = topk, device
    @torch.no_grad()
    def __call__(self, img):
        x = self.p(images=img, return_tensors="pt").to(self.dev)
        fmap = self.m.image_embedder(pixel_values=x["pixel_values"])[0]
        b, h, w, d = fmap.shape; feats = fmap.reshape(b, h*w, d)
        obj = self.m.objectness_predictor(feats).sigmoid()[0]
        boxes = self.m.box_predictor(feats, fmap)[0]  # cxcywh in padded-square coords [0,1]
        S = max(img.size); res = []
        for j in obj.topk(self.k).indices.tolist():
            cx, cy, bw, bh = (boxes[j] * S).tolist()
            x0, y0, x1, y1 = max(0, cx-bw/2), max(0, cy-bh/2), min(img.size[0], cx+bw/2), min(img.size[1], cy+bh/2)
            if x1-x0 > 16 and y1-y0 > 16: res.append((int(x0), int(y0), int(x1), int(y1)))
        return res

# ---------------- embedder ----------------
class SimpleDinoProcessor:
    """Torchvision-free equivalent of DINOv3ViTImageProcessor defaults: resize 224x224 bilinear, ImageNet mean/std."""
    def __init__(self, size=224):
        self.size = size; self.mean = np.array([0.485, 0.456, 0.406]); self.std = np.array([0.229, 0.224, 0.225])
    def __call__(self, images, return_tensors="pt"):
        x = np.stack([(np.asarray(im.convert("RGB").resize((self.size, self.size), Image.BILINEAR)) / 255.0 - self.mean) / self.std for im in images])
        return {"pixel_values": torch.tensor(x.transpose(0, 3, 1, 2), dtype=torch.float32)}

class Embedder:
    """clip: openai/clip-vit-base-patch32 | siglip2: google/siglip2-base-patch16-224 | dinov2: facebook/dinov2-small
    (dinov3 e.g. facebook/dinov3-vits16-pretrain-lvd1689m is gated: needs HF token + license acceptance)."""
    def __init__(self, name="openai/clip-vit-base-patch32", device=None):
        self.name = name; self.dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if "embeddinggemma" in name.lower() or "eg2" in os.path.basename(str(name)).lower():  # EmbeddingGemma 2 (multimodal, Apache-2.0) via sentence-transformers
            from sentence_transformers import SentenceTransformer
            self.kind = "st"; self.m = SentenceTransformer(name, device=self.dev, model_kwargs={"dtype": {"fp16": torch.float16, "bf16": torch.bfloat16, "fp32": torch.float32}[os.environ.get("DE12_EG2_DTYPE") or ("fp16" if self.dev == "cuda" else "fp32")]}); return  # v8: fp16 on GPU = same R@1/mAP as fp32 on 70-video hard, 2.3x faster
        self.m = AutoModel.from_pretrained(name).to(self.dev).eval()
        self.kind = "dino" if ("dino" in name.lower() or "dino" in getattr(self.m.config, "model_type", "")) else "vl"
        if self.kind == "dino":
            try: self.p = AutoImageProcessor.from_pretrained(name)
            except ImportError: self.p = SimpleDinoProcessor()  # DINOv3 processor needs torchvision (broken on box)
        else: self.p = AutoProcessor.from_pretrained(name)
    @torch.no_grad()
    def __call__(self, images, bs=32):
        if self.kind == "st":
            return np.asarray(self.m.encode([{"image": im.convert("RGB").resize((224, 224))} for im in images], batch_size=bs, normalize_embeddings=True), dtype="float32")
        out = []
        for i in range(0, len(images), bs):
            x = self.p(images=images[i:i+bs], return_tensors="pt"); x = {k: v.to(self.dev) for k, v in x.items()}
            if self.kind == "dino":
              with torch.autocast("cuda", dtype=torch.float16, enabled=(self.dev == "cuda" and os.environ.get("DE12_FP16", "1") == "1")):
                h = self.m(pixel_values=x["pixel_values"]).last_hidden_state
                nreg = getattr(self.m.config, "num_register_tokens", 0) or 0  # DINOv3 has 4 register tokens
                f = torch.cat([h[:, 0], h[:, 1 + nreg:].mean(1)], -1)  # CLS + mean patch
            else:
                f = self.m.get_image_features(pixel_values=x["pixel_values"])
                if not isinstance(f, torch.Tensor): f = f.pooler_output
            out.append(torch.nn.functional.normalize(f.float(), dim=-1).cpu().numpy())
        return np.concatenate(out).astype("float32")

# ---------------- index ----------------
def build_index(video_dir, out_dir, model="openai/clip-vit-base-patch32", fps=1.0, regions="grid", log=print, dedup=0):
    os.makedirs(out_dir, exist_ok=True); emb = Embedder(model)
    sam = None
    if "sam3" in regions:
        from vsearch.sam3_regions import SAM3Regions, masked_crop; sam = SAM3Regions(); prop = grid_regions if regions == "grid+sam3" else None
        R_SAM = {"boxes": 0}
    else:
        prop = OWLv2Regions(device=emb.dev) if regions == "owlv2" else (grid_regions if regions == "grid" else None)
    vecs, meta, nf, t0 = [], [], 0, time.time()
    for v in sorted(f for f in glob.glob(os.path.join(video_dir, "*")) if f.lower().endswith(VIDEO_EXT)):
        for t, img in sample_frames(v, fps, dedup):
            crops, m = [img], [{"video": os.path.basename(v), "t": round(t, 3), "kind": "frame", "box": None}]
            if prop:
                for b in prop(img):
                    crops.append(img.crop(b)); m.append({"video": m[0]["video"], "t": m[0]["t"], "kind": "region", "box": b})
            if sam:
                for b, mk in zip(sam(img), sam.last_masks):
                    crops.append(masked_crop(img, b, mk)); m.append({"video": m[0]["video"], "t": m[0]["t"], "kind": "region_sam", "box": list(b)}); R_SAM["boxes"] += 1
            vecs.append(emb(crops)); meta += m; nf += 1
    X = np.concatenate(vecs); dt = time.time() - t0
    for kind in ("frame", "region", "region_sam"):
        ids = np.array([i for i, x in enumerate(meta) if x["kind"] == kind], dtype="int64")
        if len(ids) == 0: continue
        idx = faiss.IndexIDMap(faiss.IndexFlatIP(X.shape[1])); idx.add_with_ids(X[ids], ids)
        faiss.write_index(idx, f"{out_dir}/{kind}.faiss")
    stats = {"model": model, "fps": fps, "regions": regions, "dedup": dedup, "frames": nf, "vectors": len(meta), "index_sec": round(dt, 1), "frames_per_sec": round(nf/dt, 2)}
    if sam: stats.update(sam_boxes=R_SAM["boxes"], sam_boxes_per_frame=round(R_SAM["boxes"]/max(1, nf), 2), sam_load=sam.load_info, sam_prompts=list(sam.prompts))
    json.dump({**stats, "meta": meta}, open(f"{out_dir}/meta.json", "w"))
    log(stats); return stats

# ---------------- search ----------------
class Searcher:
    def __init__(self, index_dir, embedder=None, hnsw_min=None, ef_search=64, query_cache=0):
        """Optional (off by default): hnsw_min=N rebuilds any index with >=N vectors as FAISS HNSW32
        (approximate; only worth it at ~1e5+ vectors, see results/RESULTS.md). query_cache=N keeps an LRU of
        N query embeddings keyed by sha256 of the image pixels, so repeated queries skip the EG2 forward pass."""
        self.d = json.load(open(f"{index_dir}/meta.json")); self.meta = self.d["meta"]
        self.emb = embedder or Embedder(self.d["model"])
        self.idx = {k: faiss.read_index(f"{index_dir}/{k}.faiss") for k in ("frame", "region", "region_sam") if os.path.exists(f"{index_dir}/{k}.faiss")}
        if hnsw_min:
            for k, ix in list(self.idx.items()):
                if ix.ntotal >= hnsw_min: self.idx[k] = to_hnsw(ix, ef_search)
        self.qcache_n = query_cache; self.qcache = {}

    def embed_query(self, img):
        if not self.qcache_n: return self.emb([img])
        import hashlib
        key = hashlib.sha256(img.mode.encode() + str(img.size).encode() + img.tobytes()).hexdigest()
        if key in self.qcache: self.qcache[key] = self.qcache.pop(key); return self.qcache[key]
        q = self.emb([img]); self.qcache[key] = q
        if len(self.qcache) > self.qcache_n: self.qcache.pop(next(iter(self.qcache)))
        return q

    def search(self, img, mode="frame", k=10, topn=200, merge_gap=None, qvec=None):
        """mode: frame | region | both. Returns ranked segments [{video,start,end,peak_t,score,box}]."""
        q = qvec if qvec is not None else self.embed_query(img); best = {}
        kinds = {"frame": ["frame"], "region": ["region"], "both": ["frame", "region"], "sam": ["region_sam"],
                 "frame+sam": ["frame", "region_sam"], "fuse": ["frame", "region", "region_sam"]}[mode]
        for kind in [k for k in kinds if k in self.idx]:
            D, I = self.idx[kind].search(q, min(topn, self.idx[kind].ntotal))
            for s, j in zip(D[0], I[0]):
                h = self.meta[j]; key = (h["video"], h["t"])
                if key not in best or s > best[key][0]: best[key] = (float(s), h["box"])
        gap = merge_gap if merge_gap is not None else 1.5 / self.d["fps"]
        return merge_segments(best, gap)[:k]

    def search_text(self, text, k=10, method="window", w=3, video=None, use_ordinal=True, translate=None):
        """Text -> moments over the frame index (needs a text-capable backbone: EG2 / SigLIP 2 / CLIP).
        Ordinal words (đầu tiên/thứ hai/cuối cùng, first/second/last) pick the n-th matching segment in time
        within `video` (or within the best-matching video if none given). See vsearch/text.py."""
        from vsearch.text import TextEncoder, text_search, parse_ordinal
        if getattr(self, "_te", None) is None or self._te_tr != translate:
            self._te, self._te_tr = TextEncoder(self.emb, translate=translate), translate
        if getattr(self, "_X", None) is None:
            ix = self.idx["frame"]; inner = faiss.downcast_index(ix.index); ids = faiss.vector_to_array(ix.id_map)
            self._X = np.zeros((len(self.meta), inner.d), "float32"); self._X[ids] = inner.reconstruct_n(0, inner.ntotal)
        clean, n = parse_ordinal(text) if use_ordinal else (text, None)
        q = self._te([clean])[0]
        if n and not video:  # pick the video first (best non-ordinal segment), then the n-th occurrence in it
            video = text_search(self.meta, self._X, q, self.d["fps"], method=method, w=w, k=1)[0]["video"]
        return text_search(self.meta, self._X, q, self.d["fps"], method=method, w=w, ordinal=n, video=video, k=k)

def to_hnsw(ix, ef_search=64, M=32):
    """Rebuild an IndexIDMap(FlatIP) as IndexIDMap(HNSWFlat, inner product), keeping ids."""
    inner = faiss.downcast_index(ix.index); ids = faiss.vector_to_array(ix.id_map).astype("int64")
    X = inner.reconstruct_n(0, inner.ntotal)
    h = faiss.IndexHNSWFlat(X.shape[1], M, faiss.METRIC_INNER_PRODUCT); h.hnsw.efSearch = ef_search
    out = faiss.IndexIDMap(h); out.add_with_ids(X, ids); return out

def merge_segments(best, gap):
    """Merge temporally adjacent hits (same video, |dt|<=gap) into segments; segment score = max hit score."""
    by_v = {}
    for (v, t), (s, b) in best.items(): by_v.setdefault(v, []).append((t, s, b))
    segs = []
    for v, hs in by_v.items():
        hs.sort(); cur = None
        for t, s, b in hs:
            if cur and t - cur["end"] <= gap:
                cur["end"] = t
                if s > cur["score"]: cur.update(score=s, peak_t=t, box=b)
            else:
                if cur: segs.append(cur)
                cur = {"video": v, "start": t, "end": t, "peak_t": t, "score": s, "box": b}
        segs.append(cur)
    return sorted(segs, key=lambda x: -x["score"])
