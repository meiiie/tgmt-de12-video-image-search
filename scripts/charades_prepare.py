"""Fixed dev/test split of the Charades-STA small subset (by video: sorted ids, every 3rd video -> dev) and machine
Vietnamese versions of each query (Helsinki-NLP/opus-mt-en-vi, local CPU) -> eval_charades/queries.json.
VI queries are MACHINE translations (not human), used only to test the Vietnamese path."""
import csv, json, cv2, torch
from transformers import MarianMTModel, MarianTokenizer
rows = list(csv.DictReader(open("data/charades/small.csv")))
vids = sorted({r["video"] for r in rows}); dev = {v for i, v in enumerate(vids) if i % 3 == 0}
n = "Helsinki-NLP/opus-mt-en-vi"; tok = MarianTokenizer.from_pretrained(n); m = MarianMTModel.from_pretrained(n).eval()
@torch.no_grad()
def tr(xs):
    x = tok(xs, return_tensors="pt", padding=True); return tok.batch_decode(m.generate(**x, num_beams=4, max_new_tokens=64), skip_special_tokens=True)
vi = []; en = [r["query"].strip() for r in rows]
for i in range(0, len(en), 16): vi += tr(en[i:i+16])
dur = {}
for v in vids:
    c = cv2.VideoCapture(f"data/charades/v/{v}.mp4"); dur[v] = round(c.get(7) / c.get(5), 3)
Q = [{"id": f"c{i}", "video": r["video"] + ".mp4", "duration": dur[r["video"]], "start": float(r["start"]), "end": float(r["end"]),
      "en": e, "vi_mt": t, "split": "dev" if r["video"] in dev else "test"} for i, (r, e, t) in enumerate(zip(rows, en, vi))]
json.dump({"source": "Charades-STA test, small subset of jwnt4/charades-sta-test (150 q / 138 videos)", "split_rule": "sorted video ids, index%3==0 -> dev",
           "queries": Q}, open("eval_charades/queries.json", "w"), ensure_ascii=False, indent=1)
print(sum(q["split"] == "dev" for q in Q), "dev /", sum(q["split"] == "test" for q in Q), "test"); [print(q["en"], "->", q["vi_mt"]) for q in Q[:6]]
