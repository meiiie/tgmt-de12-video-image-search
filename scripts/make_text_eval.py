"""Build the Đề 12 text-query eval set (data/text_eval/):
  A) moment queries: 30 DAVIS-2017 sequences already concatenated in data/davis_bench/videos (3 per video),
     one EN + one VI caption each (hand-written from the frames, captions.json) -> GT = sequence time span.
  B) ordinal queries: 2 composite videos re-cut from the same DAVIS clips where a category repeats
     (dogs / cars / farm animals), queries 'the first/second/last <category>' in EN + VI.
DAVIS 2017 (https://davischallenge.org/) is released for research under CC BY-NC (videos' original licences)."""
import json, cv2, os
B = "data/davis_bench"; O = "data/text_eval"; os.makedirs(f"{O}/videos", exist_ok=True)
span = {q["seq"]: q["gt"][0] for q in json.load(open(f"{B}/queries_scene.json"))}
cap_ = json.load(open(f"{O}/captions.json"))
moment = [{"id": f"m_{s}_{l}", "lang": l, "text": cap_[s][i], "ordinal": None,
           "gt": [{"video": span[s]["video"], "start": round(span[s]["start"], 3), "end": round(span[s]["end"], 3)}]}
          for s in cap_ for i, l in enumerate(("en", "vi"))]
COMP = {"ord_a.mp4": ["dog", "car-roundabout", "cows", "libby", "drift-straight", "pigs", "dogs-jump", "car-shadow", "goat"],
        "ord_b.mp4": ["goat", "car-shadow", "dogs-jump", "pigs", "drift-straight", "libby", "cows", "car-roundabout", "dog"]}
CAT = {"dog": {"dog", "libby", "dogs-jump"}, "car": {"car-roundabout", "drift-straight", "car-shadow"}, "farm": {"cows", "pigs", "goat"}}
Q = {("dog", "first"): ("the first time a dog appears", "lần đầu tiên con chó xuất hiện"),
     ("dog", "second"): ("the second time a dog appears", "lần thứ hai con chó xuất hiện"),
     ("dog", "last"): ("the last time a dog appears", "lần cuối cùng con chó xuất hiện"),
     ("car", "first"): ("the first car driving by", "chiếc ô tô đầu tiên chạy qua"),
     ("car", "second"): ("the second car driving by", "chiếc ô tô thứ hai chạy qua"),
     ("car", "last"): ("the last car driving by", "chiếc ô tô cuối cùng chạy qua"),
     ("farm", "first"): ("the first farm animal", "con vật nông trại đầu tiên"),
     ("farm", "last"): ("the last farm animal", "con vật nông trại cuối cùng")}
ordinal = []
for name, seqs in COMP.items():
    w = None; t = 0.0; spans = {}
    for s in seqs:
        g = span[s]; cap = cv2.VideoCapture(f"{B}/videos/{g['video']}"); fps = cap.get(cv2.CAP_PROP_FPS)
        cap.set(cv2.CAP_PROP_POS_MSEC, g["start"] * 1000); n = 0
        while True:
            ok, f = cap.read()
            if not ok or cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 > g["end"] + 1e-3: break
            if w is None: w = cv2.VideoWriter(f"{O}/videos/{name}", cv2.VideoWriter_fourcc(*"mp4v"), fps, (f.shape[1], f.shape[0]))
            w.write(cv2.resize(f, (w_ := f.shape[1], f.shape[0]))); n += 1
        spans[s] = (round(t, 3), round(t + n / fps, 3)); t += n / fps; cap.release()
    w.release()
    for (c, o), (en, vi) in Q.items():
        occ = sorted(spans[s] for s in seqs if s in CAT[c]); k = {"first": 0, "second": 1, "last": -1}[o]
        for l, txt in (("en", en), ("vi", vi)):
            ordinal.append({"id": f"o_{name[:-4]}_{c}_{o}_{l}", "lang": l, "text": txt, "ordinal": o, "category": c,
                            "gt": [{"video": name, "start": occ[k][0], "end": occ[k][1]}],
                            "distractor_spans": [{"video": name, "start": a, "end": b} for a, b in occ if (a, b) != occ[k]]})
    print(name, spans)
json.dump({"moment": moment, "ordinal": ordinal, "composite": {k: v for k, v in COMP.items()}}, open(f"{O}/queries_text.json", "w"), ensure_ascii=False, indent=1)
print(len(moment), "moment +", len(ordinal), "ordinal queries")
