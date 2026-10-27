"""Perception Encoder (facebook PE-Core, Apache-2.0) via open_clip weights timm/PE-Core-*. Same interface as Embedder for images + a text encoder."""
import numpy as np, torch, open_clip
class PEEmbedder:
    def __init__(self, name="timm/PE-Core-B-16"):
        self.name = name; self.m, _, self.pre = open_clip.create_model_and_transforms("hf-hub:" + name); self.m.eval(); self.tok = open_clip.get_tokenizer("hf-hub:" + name)
    @torch.no_grad()
    def __call__(self, imgs):
        f = self.m.encode_image(torch.stack([self.pre(i.convert("RGB")) for i in imgs])); return torch.nn.functional.normalize(f, dim=-1).numpy().astype("float32")
    @torch.no_grad()
    def text(self, texts):
        f = self.m.encode_text(self.tok(texts)); return torch.nn.functional.normalize(f, dim=-1).numpy().astype("float32")
