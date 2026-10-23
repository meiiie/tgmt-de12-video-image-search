"""Build a small video-retrieval benchmark from DAVIS 2017 val (480p, annotations CC BY 4.0).
- Concatenates `--per_video` sequences into one mp4 (24 fps) -> data/davis_videos
- Object queries: crop (mask bbox +15% pad) of each annotated object in a held-out frame (first `--holdout` frames
  of each sequence are NOT written to the videos, so the query frame is never indexed).
- Scene queries: the full held-out frame.
- GT: intervals (sec) in the concatenated video where the object mask is non-empty / where the sequence plays."""
import argparse, os, json, glob, cv2, numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("--davis", default="data/DAVIS"); ap.add_argument("--out", default="data/davis_bench")
ap.add_argument("--per_video", type=int, default=3); ap.add_argument("--max_seqs", type=int, default=30); ap.add_argument("--holdout", type=int, default=12); ap.add_argument("--fps", type=int, default=24)
a = ap.parse_args()
seqs = open(f"{a.davis}/ImageSets/2017/val.txt").read().split()[:a.max_seqs]
os.makedirs(f"{a.out}/videos", exist_ok=True); os.makedirs(f"{a.out}/queries", exist_ok=True)
oq, sq = [], []
def intervals(flags, off):
    out, s = [], None
    for i, f in enumerate(flags + [False]):
        if f and s is None: s = i
        if not f and s is not None: out.append((off + s / a.fps, off + (i - 1) / a.fps)); s = None
    return out
for vi in range(0, len(seqs), a.per_video):
    group = seqs[vi:vi + a.per_video]; vname = f"davis_{vi // a.per_video:02d}.mp4"; wr = None; off = 0.0
    for seq in group:
        jp = sorted(glob.glob(f"{a.davis}/JPEGImages/480p/{seq}/*.jpg")); an = sorted(glob.glob(f"{a.davis}/Annotations/480p/{seq}/*.png"))
        masks = [np.array(Image.open(p)) for p in an]; ids = sorted(set(np.unique(masks[0])) - {0})
        q = cv2.imread(jp[0]); H, W = q.shape[:2]
        cv2.imwrite(f"{a.out}/queries/{seq}_scene.jpg", q)
        kept = range(a.holdout, len(jp)); n = len(kept)
        sq.append({"image": f"queries/{seq}_scene.jpg", "seq": seq, "gt": [{"video": vname, "start": off, "end": off + (n - 1) / a.fps}]})
        for oid in ids:
            ys, xs = np.where(masks[0] == oid)
            if len(xs) < 400: continue
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max(); px, py = int(.15 * (x1 - x0)), int(.15 * (y1 - y0))
            cv2.imwrite(f"{a.out}/queries/{seq}_obj{oid}.jpg", q[max(0, y0-py):min(H, y1+py), max(0, x0-px):min(W, x1+px)])
            flags = [bool((masks[i] == oid).sum() > 200) for i in kept]
            oq.append({"image": f"queries/{seq}_obj{oid}.jpg", "seq": seq, "area_frac": round(len(xs) / (H * W), 4),
                       "gt": [{"video": vname, "start": s, "end": e} for s, e in intervals(flags, off)]})
        for i in kept:
            f = cv2.imread(jp[i])
            if f.shape[:2] != (480, 854): f = cv2.resize(f, (854, 480))
            if wr is None: wr = cv2.VideoWriter(f"{a.out}/videos/{vname}", cv2.VideoWriter_fourcc(*"mp4v"), a.fps, (854, 480))
            wr.write(f)
        off += n / a.fps
    wr.release()
json.dump(oq, open(f"{a.out}/queries_object.json", "w"), indent=1); json.dump(sq, open(f"{a.out}/queries_scene.json", "w"), indent=1)
print(f"{len(seqs)} seqs -> {len(glob.glob(a.out+'/videos/*'))} videos; {len(oq)} object queries, {len(sq)} scene queries")
