"""SAM 3 region proposals (GPU; CPU works with bf16 autocast). v4 fixes:
- Generic prompt "object" scores ~0.02-0.08 (verified on box CPU with official truck.jpg: "truck" 0.863, "object" 0.079),
  so we use a concept vocabulary of DAVIS/COCO-like class names (DEFAULT_PROMPTS) instead.
- Processor built with confidence_threshold=0.0 (its default 0.5 silently drops boxes); we filter with min_score ourselves.
- Precision: fp32 by default (DE12_SAM_FP16=1 to use fp16 autocast); on CPU the repo needs bf16 autocast.
__call__(img) -> list of xyxy boxes; self.last_masks holds the matching bool masks (HxW numpy) for masked crops."""
import os, contextlib, numpy as np
from PIL import Image

DEFAULT_PROMPTS = ("person", "animal", "dog", "horse", "cow", "bird", "car", "bicycle", "motorcycle", "boat", "ball", "vehicle")

class SAM3Regions:
    def __init__(self, prompts=None, topk=8, min_score=0.3, device=None, checkpoint_path=None):
        import torch
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        self.dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint_path = checkpoint_path or os.environ.get("SAM3_CKPT"); self.strict = os.environ.get("SAM3_STRICT", "0") == "1"
        bpe = os.environ.get("SAM3_BPE")
        model = build_sam3_image_model(device="cpu", load_from_HF=False, **({"bpe_path": bpe} if bpe else {}))
        self.load_info = {}
        if checkpoint_path:
            ck = torch.load(checkpoint_path, map_location="cpu", weights_only=True, mmap=True); ck = ck.get("model", ck)
            sd = {k.replace("detector.", "", 1): v for k, v in ck.items() if k.startswith("detector.")}
            r = model.load_state_dict(sd, strict=False)
            self.load_info = {"ckpt": os.path.basename(checkpoint_path), "detector_keys": len(sd), "missing": len(r.missing_keys), "unexpected": len(r.unexpected_keys),
                              "missing_sample": r.missing_keys[:5], "unexpected_sample": r.unexpected_keys[:5]}
            print("SAM3 load:", self.load_info); del ck, sd
            if self.strict and self.load_info["missing"]: raise RuntimeError(f"SAM3 strict load: missing={self.load_info['missing']}")
        model = model.to(self.dev).eval()
        self.proc = Sam3Processor(model, device=self.dev, confidence_threshold=0.0)
        env_p = os.environ.get("SAM3_PROMPTS")
        self.prompts = tuple(prompts or (env_p.split(",") if env_p else DEFAULT_PROMPTS)); self.k, self.th = topk, min_score
        self.last_masks, self.last_scores = [], []
    def _ctx(self):
        import torch
        if self.dev == "cpu": return torch.autocast("cpu", dtype=torch.bfloat16)
        if os.environ.get("DE12_SAM_FP16", "0") == "1": return torch.autocast("cuda", dtype=torch.float16)
        return contextlib.nullcontext()
    def raw(self, img, prompt):
        """max score + boxes for one prompt (used by the sanity check)."""
        import torch
        with self._ctx(), torch.inference_mode():
            st = self.proc.set_image(img); o = self.proc.set_text_prompt(prompt=prompt, state=st)
        s = o["scores"].float()
        return {"max_score": round(float(s.max()) if len(s) else 0.0, 3), "n_ge_th": int((s >= self.th).sum())}
    def __call__(self, img: Image.Image):
        import torch
        res = []
        with self._ctx(), torch.inference_mode():
            st = self.proc.set_image(img)
            for p in self.prompts:
                o = self.proc.set_text_prompt(prompt=p, state=st)
                for b, s, m in zip(o["boxes"].float().tolist(), o["scores"].float().tolist(), o["masks"]):
                    if s >= self.th: res.append((s, tuple(int(v) for v in b), m))
        res.sort(key=lambda x: -x[0]); keep = []
        for s, b, m in res:  # simple NMS across prompts (IoU > 0.7 = duplicate)
            if all(_iou(b, k[1]) <= 0.7 for k in keep): keep.append((s, b, m))
            if len(keep) == self.k: break
        self.last_masks = [k[2][0].cpu().numpy() if k[2].dim() == 3 else k[2].cpu().numpy() for k in keep]
        self.last_scores = [k[0] for k in keep]
        return [k[1] for k in keep]

def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u > 0 else 0.0

def masked_crop(img, box, mask, fill=(124, 116, 104)):
    """Crop to box with pixels outside the SAM mask replaced by ImageNet-mean gray -> DINOv3 pools only object patches."""
    a = np.asarray(img.convert("RGB")).copy(); a[~mask.astype(bool)] = fill
    return Image.fromarray(a).crop(box)
