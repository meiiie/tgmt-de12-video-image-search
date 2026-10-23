"""Offline weights from Kaggle datasets (no HF downloads). Supports:
 - HF-style folders (config.json + *.safetensors) anywhere under /kaggle/input
 - flat files named '<model>__<file>' (e.g. holilihu/de7-weights) -> re-assembled into /kaggle/working/w/<model>/ via symlinks
 - split checkpoints '<name>_part_NN' (+ optional '<name>_sha256.txt') -> concatenated into /kaggle/working/w/<name>.pt
Returns dict with dinov3 / sam31_ckpt / sam3_ckpt / clip paths and the logged layout."""
import glob, os, json, hashlib, shutil, re

def discover(inputs="/kaggle/input", work="/kaggle/working/w", log=print, verify_sha=True):
    files = sorted(p for p in glob.glob(f"{inputs}/**/*", recursive=True) if os.path.isfile(p))
    out = {"layout": [f"{os.path.relpath(p, inputs)} ({os.path.getsize(p)/2**20:.1f} MB)" for p in files]}
    for l in out["layout"]: log("  ", l)
    os.makedirs(work, exist_ok=True)
    # flat '<model>__<file>'
    for p in files:
        b = os.path.basename(p)
        if "__" in b:
            m, f = b.split("__", 1); d = f"{work}/{m}"; os.makedirs(d, exist_ok=True)
            if not os.path.exists(f"{d}/{f}"): os.symlink(p, f"{d}/{f}")
    # split checkpoints
    parts = {}
    for p in files:
        m = re.match(r"(.+)_part_(\d+)$", os.path.basename(p))
        if m: parts.setdefault((os.path.dirname(p), m.group(1)), []).append(p)
    for (d, name), ps in parts.items():
        dst = f"{work}/{name}.pt"
        if not os.path.exists(dst):
            with open(dst, "wb") as w:
                for p in sorted(ps): shutil.copyfileobj(open(p, "rb"), w, 1 << 24)
        out[f"{name}_ckpt_raw"] = dst
        sha = glob.glob(f"{d}/{name}_sha256*")
        if sha and verify_sha:
            want = open(sha[0]).read().split()[0].strip().lower(); h = hashlib.sha256()
            with open(dst, "rb") as f:
                for blk in iter(lambda: f.read(1 << 24), b""): h.update(blk)
            out[f"{name}_sha256_ok"] = (h.hexdigest() == want); log(f"{name}: sha256 ok={out[f'{name}_sha256_ok']}")
    hf = sorted({os.path.dirname(p) for p in glob.glob(f"{inputs}/**/config.json", recursive=True) + glob.glob(f"{work}/*/config.json")
                 if glob.glob(os.path.join(os.path.dirname(p), "*.safetensors"))})
    pick = lambda *k: next((d for d in hf if all(x in d.lower() for x in k)), None)
    out.update(dinov3=pick("dinov3", "vits16") or pick("dinov3"), dinov3_b=pick("dinov3", "vitb16"), clip=pick("clip"), dinov2=pick("dinov2"))
    ck = [p for p in files if p.endswith((".pt", ".pth"))] + [v for k, v in out.items() if k.endswith("_ckpt_raw")]
    out["sam31_ckpt"] = next((p for p in ck if re.search(r"sam3[._]?1|sam31|multiplex", os.path.basename(p).lower())), None)
    out["sam3_ckpt"] = next((p for p in ck if os.path.basename(p).lower() == "sam3.pt"), None)
    return out
