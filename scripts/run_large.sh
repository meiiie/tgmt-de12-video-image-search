#!/bin/bash
# Large-set eval (70 videos). Resumable: skips existing indexes / result files.
export TRANSFORMERS_VERBOSITY=error; B=data/davis_bench_large
[ -f data/L_clip/meta.json ] || python scripts/build_index.py --videos $B/videos --out data/L_clip --model openai/clip-vit-base-patch32 --regions none
[ -f data/L_dinov3/meta.json ] || python scripts/build_index.py --videos $B/videos --out data/L_dinov3 --model facebook/dinov3-vits16-pretrain-lvd1689m --regions grid
for Q in object_hard object; do
  [ -f results/L_clip_$Q.json ] || python scripts/evaluate.py --index data/L_clip --queries $B/queries_$Q.json --modes frame --out results/L_clip_$Q.json
  [ -f results/L_dinov3_$Q.json ] || python scripts/evaluate.py --index data/L_dinov3 --queries $B/queries_$Q.json --out results/L_dinov3_$Q.json
done
echo ALLDONE
