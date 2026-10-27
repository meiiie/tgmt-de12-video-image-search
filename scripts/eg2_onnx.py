"""Box CPU: export EG2 (ST forward, image input) to ONNX, run with onnxruntime fp32 and ORT dynamic int8.
Saves q_eg2_onnx{fp32,int8}cpu_object_hard.npy + timings into --out/cpu_variants.json."""
import argparse, json, os, sys, time, numpy as np, torch
from PIL import Image
from sentence_transformers import SentenceTransformer
ap = argparse.ArgumentParser(); ap.add_argument("--eg2", required=True); ap.add_argument("--bench", default="data/davis_bench"); ap.add_argument("--out", required=True); a = ap.parse_args()
Q = json.load(open(f"{a.bench}/queries_object_hard.json")); ims = [Image.open(os.path.join(a.bench, q["image"])).convert("RGB").resize((224, 224)) for q in Q]
p = f"{a.out}/cpu_variants.json"; res = json.load(open(p)) if os.path.exists(p) else {}
m = SentenceTransformer(a.eg2, device="cpu", model_kwargs={"dtype": torch.float32}).eval()
f = m.preprocess([{"image": ims[0]}]); keys = [k for k, v in f.items() if torch.is_tensor(v)]
class W(torch.nn.Module):
    def __init__(s, m): super().__init__(); s.m = m
    def forward(s, *xs): return s.m.forward(dict(zip(keys, xs)))["sentence_embedding"]
info = {"inputs": {k: list(f[k].shape) for k in keys}}
try:
    t = time.time()
    with torch.inference_mode(): torch.onnx.export(W(m), tuple(f[k] for k in keys), "/tmp/eg2onnx/eg2.onnx", input_names=keys, opset_version=18, dynamo=True, external_data=True)
    info.update(export_ok=True, export_s=round(time.time() - t, 1))
except Exception as e:
    try:
        t = time.time(); torch.onnx.export(W(m), tuple(f[k] for k in keys), "/tmp/eg2onnx/eg2.onnx", input_names=keys, opset_version=17, dynamo=False)
        info.update(export_ok=True, export_s=round(time.time() - t, 1), export_fallback="torchscript", dynamo_error=repr(e)[:300])
    except Exception as e2: info.update(export_ok=False, error=repr(e)[:300], error_ts=repr(e2)[:300])
res["onnx"] = info; json.dump(res, open(p, "w"), indent=1); print(info, flush=True)
if info.get("export_ok"):
    import onnxruntime as ort
    from onnxruntime.quantization import quantize_dynamic, QuantType
    try: quantize_dynamic("/tmp/eg2onnx/eg2.onnx", "/tmp/eg2onnx/eg2_int8.onnx", weight_type=QuantType.QInt8, use_external_data_format=True); info["int8_ok"] = True
    except Exception as e: info["int8_error"] = repr(e)[:300]
    for tag, path in (("onnxfp32cpu", "/tmp/eg2onnx/eg2.onnx"), ("onnxint8cpu", "/tmp/eg2onnx/eg2_int8.onnx")):
        if not os.path.exists(path): continue
        try:
            s = ort.InferenceSession(path, providers=["CPUExecutionProvider"]); names = [i.name for i in s.get_inputs()]
            def enc(im):
                g = m.preprocess([{"image": im}]); v = s.run(None, {n: g[n].numpy() for n in names})[0]; return v / np.linalg.norm(v, axis=-1, keepdims=True)
            enc(ims[0]); vs, ts = [], []
            for im in ims:
                t = time.perf_counter(); vs.append(enc(im).astype("float32")); ts.append(time.perf_counter() - t)
            np.save(f"{a.out}/q_eg2_{tag}_object_hard.npy", np.concatenate(vs)); res[tag] = {"encode_ms_mean": round(1000*np.mean(ts), 1), "encode_ms_p50": round(1000*np.median(ts), 1), "n": len(ims)}
        except Exception as e: res[tag] = {"error": repr(e)[:300]}
        print(tag, res[tag], flush=True); json.dump(res, open(p, "w"), indent=1)
