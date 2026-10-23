"""SAM 3.1 region proposals (GPU only; UNTESTED on box – no CUDA). Needs: git clone facebookresearch/sam3 && pip install -e .,
HF_TOKEN with access to facebook/sam3 / facebook/sam3.1. API per repo README (image model + Sam3Processor + text prompt).
Usage: build_index(..., regions="sam3") -> boxes of all instances matching the prompts, then embedded as region crops."""
from PIL import Image

class SAM3Regions:
    def __init__(self, prompts=("object",), topk=8, min_score=0.3):
        from sam3.model_builder import build_sam3_image_model
        from sam3.model.sam3_image_processor import Sam3Processor
        self.proc = Sam3Processor(build_sam3_image_model()); self.prompts, self.k, self.th = prompts, topk, min_score
    def __call__(self, img: Image.Image):
        state = self.proc.set_image(img); res = []
        for p in self.prompts:
            out = self.proc.set_text_prompt(state=state, prompt=p)
            for b, s in zip(out["boxes"].tolist(), out["scores"].tolist()):
                if s >= self.th: res.append((s, tuple(int(v) for v in b)))  # xyxy pixels (verify in repo)
        return [b for _, b in sorted(res, reverse=True)[: self.k]]
