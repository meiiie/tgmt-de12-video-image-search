"""Small declared text diagnostics: sentiment, answer similarity, lesson retrieval.

These hand-authored examples are not a benchmark of video sentiment, pronunciation,
IELTS scoring, or real-world product quality. Keep every result, including failures.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", choices=("bf16", "fp32"), default="bf16")
    args = parser.parse_args()
    raw = args.cases.read_bytes()
    cases = json.loads(raw)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    import torch
    from sentence_transformers import SentenceTransformer
    assert torch.cuda.is_available()
    if args.dtype == "bf16":
        assert torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float32
    torch.set_num_threads(4)
    start = time.perf_counter()
    model = SentenceTransformer(str(args.model), device="cuda", local_files_only=True,
        config_kwargs={"vision_config": None, "audio_config": None}, model_kwargs={"dtype": dtype})
    report = {"cases_sha256": hashlib.sha256(raw).hexdigest(), "model_path": str(args.model.resolve()),
        "model_config_sha256": hashlib.sha256((args.model / "config.json").read_bytes()).hexdigest(),
        "model_load_seconds": time.perf_counter() - start, "torch": torch.__version__,
        "dtype": str(dtype), "dimension": 768, "source": cases["description"], "sentiment": {}}

    def encode(texts, prompt):
        vectors = np.asarray(model.encode(texts, prompt_name=prompt, batch_size=8,
            normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        assert vectors.shape == (len(texts), 768) and np.isfinite(vectors).all() and np.all(norms > 1e-9)
        return vectors / norms

    sample_vectors = encode([c["text"] for c in cases["sentiment"]], "Classification")
    for language, definitions in cases["labels"].items():
        names = list(definitions)
        scores = sample_vectors @ encode(list(definitions.values()), "Classification").T
        items = [{**case, "predicted": names[int(row.argmax())],
                  "scores": {label: float(score) for label, score in zip(names, row)}}
                 for case, row in zip(cases["sentiment"], scores)]
        groups = {}
        for group in ("plain", "challenge"):
            subset = [x for x in items if x["group"] == group]
            groups[group] = {"total": len(subset), "correct": sum(x["label"] == x["predicted"] for x in subset)}
        report["sentiment"][language] = {"label_definitions": definitions, "groups": groups, "items": items}

    pairs = cases["grading_pairs"]
    vectors = encode([c[key] for c in pairs for key in ("reference", "correct", "incorrect")], "STS")
    report["grading_similarity"] = []
    for i, case in enumerate(pairs):
        reference, correct, incorrect = vectors[i * 3:i * 3 + 3]
        report["grading_similarity"].append({**case, "correct_similarity": float(reference @ correct),
            "incorrect_similarity": float(reference @ incorrect),
            "incorrect_ranks_higher": bool(reference @ incorrect > reference @ correct)})

    documents = cases["learning_documents"]
    document_vectors = encode([x["text"] for x in documents], "Document")
    query_vectors = encode([x["text"] for x in cases["learning_queries"]], "SearchQuery")
    report["learning_retrieval"] = []
    for query, scores in zip(cases["learning_queries"], query_vectors @ document_vectors.T):
        order = np.argsort(-scores)
        report["learning_retrieval"].append({**query, "top1_correct": documents[int(order[0])]["id"] == query["expected"],
            "results": [{**documents[int(i)], "similarity": float(scores[i])} for i in order]})
    report["summary"] = {
        "sentiment": {lang: result["groups"] for lang, result in report["sentiment"].items()},
        "incorrect_answer_ranks_higher": sum(x["incorrect_ranks_higher"] for x in report["grading_similarity"]),
        "grading_pairs": len(pairs),
        "learning_top1_correct": sum(x["top1_correct"] for x in report["learning_retrieval"]),
        "learning_queries": len(cases["learning_queries"]),
        "learning_documents": len(documents),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
