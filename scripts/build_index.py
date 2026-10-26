import argparse, sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsearch.core import build_index
ap = argparse.ArgumentParser(); ap.add_argument("--videos", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--model", default="google/embeddinggemma-2", help="default EG2 (Kaggle v7 winner); DINOv3: facebook/dinov3-vits16-pretrain-lvd1689m --regions grid"); ap.add_argument("--fps", type=float, default=1.0)
ap.add_argument("--regions", default=None, choices=["none", "grid", "owlv2", "sam3", "grid+sam3"]); ap.add_argument("--dedup", type=int, default=0, help="aHash hamming threshold, 0=off"); a = ap.parse_args()
if a.regions is None: a.regions = "none" if ("embeddinggemma" in a.model.lower() or "eg2" in os.path.basename(a.model).lower()) else "grid"  # EG2: frame-only is best
build_index(a.videos, a.out, a.model, a.fps, a.regions, dedup=a.dedup)
