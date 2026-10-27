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
- 09:55 27/10 v8 task (speed+accuracy: fusion, two-stage, EG2 profiling/fp16/int8/Matryoshka/FAISS, SAM on EG2 top-20).
  Box has only 10 videos (no distractors) -> need GPU kernel v8 that dumps ALL embeddings (scripts/dump_embeddings.py, stages dino/eg2_fp32/eg2_fp16/sam/samemb) into one results JSON; all experiments then run OFFLINE on box (scripts/offline_v8.py).
  Both Kaggle slots busy at 09:50 (de7-v6-sam-boxprompt, de14-helmet-sam31-dinov3). Box: EG2+DINOv3 weights -> /tmp/eg2w,/tmp/d3w (delete after), libs /tmp/eglib; CPU profiling of EG2 query encode (fp32/bf16/int8 dyn quant/ONNX) on box.
- 10:05 box smoke OK (10 videos): dump stages dino+eg2_fp32 on CPU, offline_v8.py reproduces 10-video baselines (DINOv3 both 0.776/0.844 CPU, EG2 0.983/0.971). EG2 CPU query: forward 1335 ms, preprocess 3.5 ms. /tmp/v8_ready set; watcher /workspace/tgmt/de12_v8_push.sh pushes v8 when <2 kernels running (log /tmp/v8_push.log). Box dump in /tmp/boxdump.
- 10:11 v8 PUSHED by watcher at 10:06 (1 kernel was running). Box CPU fp32 query encode done; int8 dyn-quant crashed on gemma4 input_proj -> excluded input_proj, rerunning eg2_cpu_variants.py (/tmp/cpuvar.log).
- 10:19 Box CPU EG2 query (58 hard q, 10-video, fp32 index): fp32 1928 ms p50 (R@1 .983 mAP .971); torch dyn-int8 (Linear except input_proj) 1128 ms, R@1 .621 mAP .760 (cos .885) BAD; bf16 640 ms, .966/.963 (cos .997). preprocess ~3 ms -> forward dominates. ONNX export running (/tmp/onnx.log, /tmp/eg2onnx). Results in /tmp/boxdump/cpu_variants.json, off.json (copy to results/ before cleanup).
- 10:30 ONNX export OK (dynamo, 76 s) but ORT fp32 CPU 5919 ms/q (3x slower than torch); EG2 image = 280 soft tokens (2520 patches) -> new knob: processor max_soft_tokens 70/140 (dump stage eg2_bf16_tok70). Downloading DAVIS to box to rebuild 70-video set (data/DAVIS, distractors via add_distractors.py; /tmp/davisdl.log) for box-CPU token-budget runs.
- 10:38 interrupted; ONNX int8 run died (not measured). v8 kernel still RUNNING (no re-push). Starting box 70-video runs -> /tmp/boxdump70 (dino, eg2_bf16_tok280/140/70), log /tmp/b70.log
- 10:50 v8 COMPLETE 10:06-10:48 no errors; dump unpacked /tmp/v8dump; results/kaggle_v8_de12_results.json (no b64). GPU T4: EG2 fp32 q 461 ms (forward 457, preprocess 7), fp16 203 ms; DINOv3 q 16.5 ms; SAM 2.71 s/frame, 1104 boxes/276 fr.
- 10:51 offline_v8 on v8 dump -> results/v8_offline.json (baselines reproduce v7 exactly)
- 11:07 README/RESULTS v8 section written; default: EG2 fp16 on CUDA (core.py). Next: commit+push, cleanup.
- 11:07 committed+pushed; temp weights/dumps/DAVIS/distractors deleted. DONE.
- 13:30 TEXT-SEARCH task start. Env: PYTHONPATH=/tmp/eglib:/tmp/egdeps:/tmp/egtv:. ; HF snapshot download (EG2, siglip2-base, clip-b32, opus-mt-vi-en) -> ~/.cache/hf, log /tmp/textdl.log. Plan: scripts/text_eval.py; eval = 30 DAVIS seq spans (EN+VI captions) + composite ordinal video.
- 13:40 eval set built (scripts/make_text_eval.py -> data/text_eval: 60 moment + 32 ordinal q). vsearch/text.py written. Indexes 4fps frame-only -> data/text_idx/<model>_{davis10,ord} via /tmp/build_text_idx.sh (log /tmp/textidx.log; resumable, skips done).
- 13:55 siglip2 eval done (results/text_siglip2-base-patch16-224.json). Searcher.search_text + app text box written (not yet run). Waiting EG2 index.
- 13:45 d3-turbo add-on: verified HF vllm-sr/d3-turbo (Apache-2.0, 52.2GB bf16), -INT4 (16.6GB, W4A16 unpack->BF16, peak 46.4GiB MI300X), -FP8, -NVFP4; vLLM-SR engine ROCm/MI325X only documented. 2.12s/255q IS stated on MI325X. Plan: T4 infeasible (doc'd), real test with small sibling d3-lite (1.7GB) on box CPU as re-ranker.
- 14:00 EG2 4fps idx done (0.42 fr/s CPU). running /tmp/evals.log chain: clip build+eval, eg2, eg2 --translate, siglip2 --translate -> results/text_*.json. d3-lite download /tmp/d3dl.log
- 14:15 evals done for clip/eg2/eg2-opusmt (siglip-opusmt chain). d3-lite rerank running (scripts/text_rerank_d3.py, /tmp/d3rr.log)
- 14:30 d3-lite rerank done results/text_rerank_d3-lite.json. Next: app e2e test, README.
- 14:45 README/RESULTS text-search section written; committing.
- 14:50 pushed a8354c5; d3-lite weights deleted. DONE (d3-turbo not run: infeasible on T4, documented).
- 14:25 soccer demo (scripts/get_soccer_demo.sh, eval_text/soccer_*), negatives, text_extra_eval.py; min_score in core/app. results/text_extra_*.json
