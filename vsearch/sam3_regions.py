"""SAM 3.1 region proposals (GPU only; box CPU run was OOM-killed (~7.2 GB RSS); intended for Kaggle GPU). Needs: git clone facebookresearch/sam3 && pip install -e .,
HF_TOKEN with access to facebook/sam3 / facebook/sam3.1. API per repo README (image model + Sam3Processor + text prompt).
Usage: build_index(..., regions="sam3") -> boxes of all instances matching the prompts, then embedded as region crops."""
from PIL import Image

class SAM3Regions:
    def __init__(self, prompts=("object",), topk=8, min_score=0.3, device=None, checkpoint_path=None):
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        import torch; device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        import os; checkpoint_path = checkpoint_path or os.environ.get("SAM3_CKPT"); self.strict = os.environ.get("SAM3_STRICT", "0") == "1"
        model = build_sam3_image_model(device="cpu", load_from_HF=checkpoint_path is None)
        self.load_info = {}
        if checkpoint_path:  # works for sam3.pt and sam3.1_multiplex.pt: take 'detector.*' keys, report mismatch
            ck = torch.load(checkpoint_path, map_location="cpu", weights_only=True); ck = ck.get("model", ck)
            sd = {k.replace("detector.", "", 1): v for k, v in ck.items() if k.startswith("detector.")}
            r = model.load_state_dict(sd, strict=False)
            self.load_info = {"ckpt": os.path.basename(checkpoint_path), "detector_keys": len(sd), "missing": len(r.missing_keys), "unexpected": len(r.unexpected_keys), "missing_sample": r.missing_keys[:5], "unexpected_sample": r.unexpected_keys[:5]}
            print("SAM3 load:", self.load_info); del ck, sd
            if self.strict and self.load_info["missing"]: raise RuntimeError(f"SAM3 strict load: missing={self.load_info['missing']}")
        model = model.to(device).eval()
        self.proc = Sam3Processor(model); self.prompts, self.k, self.th = prompts, topk, min_score
    def __call__(self, img: Image.Image):
        import torch, os, contextlib
        fp16 = torch.cuda.is_available() and os.environ.get("DE12_FP16", "1") == "1"
        with (torch.autocast("cuda", dtype=torch.float16) if fp16 else contextlib.nullcontext()), torch.inference_mode():
            return self._call(img)
    def _call(self, img):
        state = self.proc.set_image(img); res = []
        for p in self.prompts:
            out = self.proc.set_text_prompt(state=state, prompt=p)
            for b, s in zip(out["boxes"].float().tolist(), out["scores"].float().tolist()):
                if s >= self.th: res.append((s, tuple(int(v) for v in b)))  # xyxy pixels (verify in repo)
        return [b for _, b in sorted(res, reverse=True)[: self.k]]
