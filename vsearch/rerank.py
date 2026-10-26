"""Region re-ranking of top-K segments: for each candidate segment, re-open its peak frame, get object proposals
(SAM 3 on GPU; grid on CPU as stand-in), embed each crop with the same encoder, and rescore the segment as
max(original, max_crop_cosine). Returns re-sorted segments + timing."""
import os, time, cv2, numpy as np
from PIL import Image

def read_frame(video_path, t):
    cap = cv2.VideoCapture(video_path); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release()
    return Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) if ok else None

_CACHE = {}  # (video, peak_t) -> proposals; each keyframe is proposed once per process

def rerank(searcher, video_dir, img, proposer, mode="both", k_in=20, k_out=10, qvec=None):
    t0 = time.time(); q = qvec if qvec is not None else searcher.emb([img])
    segs = searcher.search(None, mode, k_in, qvec=q); n_props = 0
    for s in segs:
        fr = read_frame(os.path.join(video_dir, s["video"]), s["peak_t"])
        if fr is None: continue
        key = (s["video"], round(s["peak_t"], 3))
        if key not in _CACHE: _CACHE[key] = proposer(fr)
        boxes = _CACHE[key]; n_props += len(boxes)
        if not boxes: continue
        E = searcher.emb([fr.crop(b) for b in boxes]); sims = E @ q[0]; j = int(sims.argmax())
        if sims[j] > s["score"]: s.update(score=float(sims[j]), box=list(boxes[j]), reranked=True)
    segs.sort(key=lambda x: -x["score"])
    return segs[:k_out], {"rerank_sec": time.time() - t0, "proposals": n_props}
