"""Large benchmark: val benchmark (10 videos, queries unchanged) + every DAVIS 2017 *train* sequence as its own
distractor video (60) -> 70 videos. Distractor sources listed in DAVIS SOURCES.md (copied to licenses_distractors.md)."""
import os, glob, shutil, cv2, json, re
src, out, D = "data/davis_bench", "data/davis_bench_large", "data/DAVIS"
os.makedirs(f"{out}/videos", exist_ok=True)
for f in glob.glob(f"{src}/videos/*.mp4"):
    d = f"{out}/videos/{os.path.basename(f)}"; os.path.exists(d) or os.symlink(os.path.abspath(f), d)
for q in ["queries", "queries_hard"]:
    d = f"{out}/{q}"; os.path.exists(d) or os.symlink(os.path.abspath(f"{src}/{q}"), d)
for j in glob.glob(f"{src}/queries_*.json"): shutil.copy(j, out)
seqs = open(f"{D}/ImageSets/2017/train.txt").read().split(); srcmd = open(f"{D}/SOURCES.md").read(); lic = []
for s in seqs:
    v = f"{out}/videos/distractor_{s}.mp4"
    if not os.path.exists(v):
        fr = sorted(glob.glob(f"{D}/JPEGImages/480p/{s}/*.jpg")); wr = cv2.VideoWriter(v, cv2.VideoWriter_fourcc(*"mp4v"), 24, (854, 480))
        for p in fr:
            im = cv2.imread(p); wr.write(im if im.shape[:2] == (480, 854) else cv2.resize(im, (854, 480)))
        wr.release()
    m = re.search(rf"\* {re.escape(s)}\s+\[Link\]\(([^)]+)\)", srcmd); lic.append(f"| distractor_{s}.mp4 | {s} | {m.group(1) if m else 'see DAVIS SOURCES.md'} |")
open("results/licenses_distractors.md", "w").write("# Distractor videos (DAVIS 2017 train)\nAnnotations: CC BY 4.0 (DAVIS organizers). Frames: from the original source videos listed by DAVIS (YouTube/Pexels/Videvo/…), redistributed by DAVIS for research; we do not redistribute videos.\n\n| video | sequence | original source |\n|---|---|---|\n" + "\n".join(lic) + "\n")
print(len(glob.glob(f"{out}/videos/*.mp4")), "videos")
