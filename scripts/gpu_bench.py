"""GPU measurements (Kaggle P100 / T4): DINOv3 embedding throughput, SAM 3 keyframe region extraction speed,
peak VRAM via torch.cuda.max_memory_allocated. Writes results/gpu_bench.json. Real numbers only."""
import json, time, glob, sys, os, torch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsearch.core import Embedder, sample_frames
assert torch.cuda.is_available(), "needs GPU"
dev = torch.cuda.get_device_name(0); R = {"gpu": dev, "torch": torch.__version__}
vids = sorted(glob.glob("data/davis_bench_large/videos/*.mp4"))[:5]
frames = [im for v in vids for _, im in sample_frames(v, 1.0)]; R["n_frames"] = len(frames)
def peak(): return round(torch.cuda.max_memory_allocated() / 2**30, 2)
torch.cuda.reset_peak_memory_stats(); e = Embedder("facebook/dinov3-vits16-pretrain-lvd1689m", "cuda"); e(frames[:4])
torch.cuda.synchronize(); t = time.time(); e(frames, bs=64); torch.cuda.synchronize()
R["dinov3_vits16"] = {"img_per_s": round(len(frames) / (time.time() - t), 1), "peak_vram_gb": peak()}
del e; torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
from vsearch.sam3_regions import SAM3Regions
t = time.time(); sam = SAM3Regions(); R["sam3_load_s"] = round(time.time() - t, 1); sam(frames[0])
torch.cuda.synchronize(); t = time.time(); nb = sum(len(sam(f)) for f in frames); torch.cuda.synchronize()
R["sam3_image"] = {"s_per_frame": round((time.time() - t) / len(frames), 3), "boxes_per_frame": round(nb / len(frames), 2), "peak_vram_gb": peak()}
print(json.dumps(R, indent=1)); os.makedirs("results", exist_ok=True); json.dump(R, open("results/gpu_bench.json", "w"), indent=1)
