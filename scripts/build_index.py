import argparse, sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vsearch.core import build_index
ap = argparse.ArgumentParser(); ap.add_argument("--videos", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--model", default="openai/clip-vit-base-patch32"); ap.add_argument("--fps", type=float, default=1.0)
ap.add_argument("--regions", default="grid", choices=["none", "grid", "owlv2", "sam3"]); ap.add_argument("--dedup", type=int, default=0, help="aHash hamming threshold, 0=off"); a = ap.parse_args()
build_index(a.videos, a.out, a.model, a.fps, a.regions, dedup=a.dedup)
