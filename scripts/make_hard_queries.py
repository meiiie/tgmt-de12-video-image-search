"""Harder object queries: each DAVIS object crop is hflipped, downscaled to 50%, brightness x0.7, and pasted on a
random-noise 224x224 canvas (removes scene context around the object). Writes queries_object_hard.json."""
import json, os, numpy as np
from PIL import Image, ImageOps, ImageEnhance
b = "data/davis_bench"; rng = np.random.default_rng(0); Q = json.load(open(f"{b}/queries_object.json")); out = []
os.makedirs(f"{b}/queries_hard", exist_ok=True)
for q in Q:
    im = ImageEnhance.Brightness(ImageOps.mirror(Image.open(f"{b}/{q['image']}").convert("RGB"))).enhance(0.7)
    im.thumbnail((112, 112)); bg = Image.fromarray(rng.integers(0, 255, (224, 224, 3), dtype=np.uint8))
    bg.paste(im, ((224 - im.width) // 2, (224 - im.height) // 2)); p = q["image"].replace("queries/", "queries_hard/")
    bg.save(f"{b}/{p}"); out.append({**q, "image": p})
json.dump(out, open(f"{b}/queries_object_hard.json", "w"), indent=1); print(len(out))
