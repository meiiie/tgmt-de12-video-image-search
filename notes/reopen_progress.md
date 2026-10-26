# Đề 12 reopen – progress (UTC+7)
- Kaggle budget: 2 runs used (v4 = failed SAM dtype + EG2 import; v5 = OK, 23:52–00:48 27/10). No more pushes.
- v5 results: results/kaggle_v5_de12_results.json (SAM 3 sanity fp16 OK: truck 0.865, DAVIS 5 frames boxes [5,8,6,1,8]).
- EG2 in kernel failed (sentence-transformers Pooling arg mismatch in --no-deps lib) -> benchmarking EG2 frame-only on box CPU (in progress, log /tmp/eg2run.log).
- README lines 12-13 fixed (commit 8e72354).
- TODO: EG2 CPU numbers -> RESULTS.md/README tables, commit, report.
