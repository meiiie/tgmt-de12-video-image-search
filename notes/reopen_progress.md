# Đề 12 reopen – progress (UTC+7)
- Kaggle budget: 2 runs used (v4 = failed SAM dtype + EG2 import; v5 = OK, 23:52–00:48 27/10). No more pushes.
- v5 results: results/kaggle_v5_de12_results.json (SAM 3 sanity fp16 OK: truck 0.865, DAVIS 5 frames boxes [5,8,6,1,8]).
- EG2 in kernel failed (sentence-transformers Pooling arg mismatch in --no-deps lib) -> benchmarking EG2 frame-only on box CPU (in progress, log /tmp/eg2run.log).
- README lines 12-13 fixed (commit 8e72354).
- TODO: EG2 CPU numbers -> RESULTS.md/README tables, commit, report.
- 01:10 Leakage audit (EG2 0.983 on 10-video hard): see notes/eg2_leakage_audit.md. Box "large70" EG2 numbers DISCARDED: box data/davis_bench_large has only 10 videos (distractors cleaned for disk) -> invalid.
- 01:20 hybrid results written to README/RESULTS. Kernel v6 (EG2 70-video, pinned ST 6.2.0/transformers 5.20.2) prepared, NOT pushed: 2 kernels running (de7-sam31-v4, de14-helmet).
- 01:25 EG2 10-video results committed; v6 auto-push watcher running (/workspace/tgmt/de12_v6_push.sh).
- 02:35 v6 push (routine; watcher gone, .venv missing so used /tmp/kv kaggle; 1 kernel running): Kernel version 6 successfully pushed.  Please check progress at https://www.kaggle.com/code/holilihu/tgmt-de12-video-image-search
- 03:35 v6 COMPLETE but EG2 FAILED: index_eg2_large70 timeout (1500s), index_eg2_small10 TypeError Pooling.__init__() missing 'embedding_dimension' (ST 6.2.0 in /tmp/eglib). No EG2 70-video numbers; app default stays DINOv3. DINOv3 same-run rerun saved results/kaggle_v6_de12_results.json (large70 object_hard both R@1 0.586 mAP@10 0.68). Routine paused.
- 03:50 v7 prep. ROOT CAUSE of EG2 Pooling error: dataset de12-embeddinggemma2 stores `eg2files__1_Poolingconfig.json` (slash lost, no '@'), so kernel created /tmp/eg2/1_Poolingconfig.json and 1_Pooling/ had no config -> Pooling() without embedding_dimension. Not an ST version issue. Fix: remap 1_Poolingconfig.json->1_Pooling/config.json, 2_Normalizeconfig.json->2_Normalize/config.json.
  Box CPU test with EXACT kernel pins (--no-deps target): sentence-transformers 6.2.0, transformers 5.20.2, huggingface_hub 1.33.0, tokenizers 0.23.2, safetensors 0.8.0 (+ box torch 2.14.1+cpu, torchvision 0.29.1+cpu): load 3.7 s, 4 hard queries -> (4,768) fp32, 9.3 s/img CPU. OK.
  Kernel v7: scripts/build_index_cached.py (per-video npy/json cache in /kaggle/working/eg2_cache, resumable); EG2 indexing own cell (<=5400 s, frame-only large70+small10 first, then grid large70 if time); no SAM rerun; DINOv3 frame+grid rerun for same-run comparison; post-setup budget 100 min.
- 03:40 v7 pushed (1 kernel running: de14-helmet).
- 04:24 interrupted; v7 still RUNNING, watcher restarted (no re-push).
- 04:33 v7 COMPLETE (49 min). EG2 frame 70-video hard R@1 0.948 mAP 0.951 vs DINOv3 0.586/0.680 -> default switched to EG2 (build_index default model/regions, README); DINOv3 selectable.
