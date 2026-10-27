"""Box CPU: EG2 query-encode variants (fp32 / bf16 / dynamic int8 Linear / ONNX attempt). Saves query vectors
q_eg2_<tag>_object_hard.npy into --out and timings into --out/cpu_variants.json."""
import argparse, json, os, sys, time, numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
from sentence_transformers import SentenceTransformer
ap = argparse.ArgumentParser(); ap.add_argument("--eg2", required=True); ap.add_argument("--bench", default="data/davis_bench"); ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=58); a = ap.parse_args()
Q = json.load(open(f"{a.bench}/queries_object_hard.json"))[:a.n]; ims = [Image.open(os.path.join(a.bench, q["image"])).convert("RGB").resize((224, 224)) for q in Q]
res = {"threads": torch.get_num_threads(), "cpu": os.popen("lscpu | grep 'Model name'").read().strip()}
p = f"{a.out}/cpu_variants.json"; res = {**(json.load(open(p)) if os.path.exists(p) else {}), **res}
def run(tag, m):
    enc = lambda im: m.encode([{"image": im}], normalize_embeddings=True)
    enc(ims[0]); vs, ts, tp = [], [], []
    for im in ims:
        t = time.perf_counter(); vs.append(np.asarray(enc(im), dtype="float32")); ts.append(time.perf_counter() - t)
    for im in ims[:10]:
        t = time.perf_counter(); f = m.preprocess([{"image": im}]); tp.append(time.perf_counter() - t)
    np.save(f"{a.out}/q_eg2_{tag}_object_hard.npy", np.concatenate(vs))
    res[tag] = {"encode_ms_mean": round(1000 * np.mean(ts), 1), "encode_ms_p50": round(1000 * np.median(ts), 1), "preprocess_ms_p50": round(1000 * np.median(tp), 1), "n": len(ims)}
    print(tag, res[tag], flush=True); json.dump(res, open(p, "w"), indent=1)
m = SentenceTransformer(a.eg2, device="cpu", model_kwargs={"dtype": torch.float32})
if "fp32cpu" not in res: run("fp32cpu", m)
import copy; LIN = {n for n, x in m.named_modules() if isinstance(x, torch.nn.Linear) and "input_proj" not in n}  # input_proj weight dtype is read directly by Gemma4 code
res["int8_linear_layers"] = len(LIN); mi = torch.ao.quantization.quantize_dynamic(copy.deepcopy(m), LIN, dtype=torch.qint8); run("int8cpu", mi); del mi
mb = SentenceTransformer(a.eg2, device="cpu", model_kwargs={"dtype": torch.bfloat16}); run("bf16cpu", mb); del mb
try:  # ONNX: export the whole ST forward on one preprocessed image
    f = m.preprocess([{"image": ims[0]}]); keys = [k for k, v in f.items() if torch.is_tensor(v)]
    class W(torch.nn.Module):
        def __init__(s, m): super().__init__(); s.m = m
        def forward(s, *xs): return s.m.forward(dict(zip(keys, xs)))["sentence_embedding"]
    t = time.time(); torch.onnx.export(W(m), tuple(f[k] for k in keys), "/tmp/eg2.onnx", input_names=keys, opset_version=18, dynamo=True)
    res["onnx_export"] = {"ok": True, "sec": round(time.time() - t, 1), "inputs": keys}
except Exception as e: res["onnx_export"] = {"ok": False, "error": repr(e)[:400]}
print(res.get("onnx_export")); json.dump(res, open(p, "w"), indent=1)
