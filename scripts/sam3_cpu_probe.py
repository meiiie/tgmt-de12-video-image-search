"""Probe SAM 3 image detector on CPU: load time + per-frame time + boxes for text prompts."""
import time, sys, cv2, torch
from PIL import Image
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
t = time.time(); m = build_sam3_image_model(device="cpu"); P = Sam3Processor(m, device="cpu") if "device" in Sam3Processor.__init__.__code__.co_varnames else Sam3Processor(m)
print("load_s", round(time.time() - t, 1), flush=True)
cap = cv2.VideoCapture("data/davis_bench/videos/davis_00.mp4"); cap.set(cv2.CAP_PROP_POS_MSEC, 2000); ok, f = cap.read()
img = Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
for p in ["object", "person", "animal"]:
    t = time.time(); st = P.set_image(img); t1 = time.time(); out = P.set_text_prompt(prompt=p, state=st)
    print(p, "set_image_s", round(t1 - t, 1), "prompt_s", round(time.time() - t1, 1), "n", len(out["scores"]), [round(s, 2) for s in out["scores"].tolist()[:5]], flush=True)
