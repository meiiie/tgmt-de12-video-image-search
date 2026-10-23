#!/bin/bash
# Final eval matrix -> results/*.json ; summary lines in results/run_final.log
export TRANSFORMERS_VERBOSITY=error
ev(){ echo "== $1 $2 $3"; python scripts/evaluate.py --index data/idx_$1 --queries data/davis_bench/queries_$2.json $3 --out results/${1}_$2$4.json 2>&1 | grep -E "^(frame|region|both)"; }
[ -f data/idx_dinov3-vits16/meta.json ] || python scripts/build_index.py --videos data/davis_bench/videos --out data/idx_dinov3-vits16 --model facebook/dinov3-vits16-pretrain-lvd1689m --fps 1 --regions grid 2>&1 | grep model
for n in dinov3-vits16 dinov2-small clip-vit-base-patch32; do
  ev $n object_hard; ev $n object "--max_area 0.05" _small
  [ $n = dinov3-vits16 ] && { ev $n object; ev $n scene; }
done
