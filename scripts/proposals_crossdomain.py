"""Does proposals mode hurt outside Charades? EG2 app path (Searcher.search_text), window vs proposals, on
DAVIS moment (10 videos, video not given), DAVIS ordinal (video given) and football (16 q). Hit = peak (proposals: centre)
inside GT +-0.5 s; also R@1 tIoU>=0.5."""
import json, sys, numpy as np
sys.path.insert(0, ".")
from vsearch.core import Searcher
def iou(a, b): i = max(0, min(a[1], b[1]) - max(a[0], b[0])); u = max(a[1], b[1]) - min(a[0], b[0]); return i / u if u else 0
Qt = json.load(open("eval_text/queries_text.json")); SOC = json.load(open("eval_text/soccer_queries.json"))["queries"]
sets = {"davis_moment": ("davis10", [(q, None) for q in Qt["moment"]]), "davis_ordinal": ("ord", [(q, q["gt"][0]["video"]) for q in Qt["ordinal"]]),
        "football": ("soccer", [(q, None) for q in SOC])}
out = {}
for name, (ix, qs) in sets.items():
    S = Searcher(f"data/text_idx/embeddinggemma-2_{ix}")
    for meth in ("window", "proposals"):
        r = {"en": [], "vi": []}
        for q, v in qs:
            s = S.search_text(q["text"], 5, method=meth, video=v)[0]
            h = any(s["video"] == g["video"] and g["start"] - .5 <= s["peak_t"] <= g["end"] + .5 for g in q["gt"])
            t = max(iou((s["start"], s["end"]), (g["start"], g["end"])) for g in q["gt"] if g["video"] == s["video"]) if any(g["video"] == s["video"] for g in q["gt"]) else 0
            r[q["lang"]].append((h, t >= .5, t))
        out[f"{name}_{meth}"] = {l: {"n": len(x), "R@1_hit": round(np.mean([a for a, _, _ in x]), 3), "R@1_tIoU0.5": round(np.mean([b for _, b, _ in x]), 3), "mIoU": round(np.mean([c for _, _, c in x]), 3)} for l, x in r.items()}
        print(name, meth, out[f"{name}_{meth}"])
json.dump(out, open("results/proposals_crossdomain.json", "w"), indent=1)
