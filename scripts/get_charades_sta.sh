#!/usr/bin/env bash
# Charades-STA test subset (150 queries / 138 videos, 683 MB) from the HF mirror jwnt4/charades-sta-test.
# Videos: Charades v1 480p (AI2, "License for Non-Commercial Use", https://prior.allenai.org/projects/data/charades/license.txt):
# academic research only, no redistribution -> never commit or publish them. Annotations: Charades-STA (Gao et al. 2017,
# arXiv:1705.02101, https://github.com/jiyanggao/TALL). Full test set: videos.zip (6.6 GB, 1334 videos) in the same repo.
set -e; D=data/charades; mkdir -p $D; cd $D; R=https://huggingface.co/datasets/jwnt4/charades-sta-test/resolve/main
curl -sL -o small.csv $R/charades-sta-test-small.csv; curl -sL -o sta_test.txt $R/charades_sta_test.txt
curl -sL -o videos_small.zip $R/videos_small.zip; unzip -q videos_small.zip -d v; rm videos_small.zip; ls v | wc -l
