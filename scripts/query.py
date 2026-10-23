import argparse, sys, os, time; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image; from vsearch.core import Searcher
ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True); ap.add_argument("--image", required=True)
ap.add_argument("--mode", default="both", choices=["frame", "region", "both"]); ap.add_argument("--k", type=int, default=5); a = ap.parse_args()
s = Searcher(a.index); t = time.time()
for r in s.search(Image.open(a.image).convert("RGB"), a.mode, a.k):
    print(f"{r['video']}\t{r['start']:.1f}-{r['end']:.1f}s (peak {r['peak_t']:.1f}s)\tscore={r['score']:.3f}")
print(f"search {1000*(time.time()-t):.0f} ms")
