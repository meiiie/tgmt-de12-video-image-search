#!/usr/bin/env bash
# Download 4 openly licensed football clips from Wikimedia Commons and join them into data/soccer/videos/match.mp4
# (640x360, 25 fps, no audio). Licences/attribution: eval_text/soccer_sources.md. Ground truth: eval_text/soccer_queries.json
set -e; D=data/soccer; mkdir -p $D/raw $D/videos; cd $D/raw; UA="de12-research/1.0 (github.com/meiiie)"; B=https://upload.wikimedia.org/wikipedia/commons
curl -sL -A "$UA" -o p0.ogv  "$B/1/17/Sa%C5%A1a_Viciknez_2006_CSL_quarterfinal_goal.ogv"
curl -sL -A "$UA" -o p1.webm "$B/d/d4/Sidemen_Charity_Match_2025_-_Sketch_Save.webm"
curl -sL -A "$UA" -o p2.webm "$B/2/20/Kald%C4%B1r%C4%B1m_scored_the_goal_for_a_3-3_draw_%28Be%C5%9Fikta%C5%9F-Fenerbah%C3%A7e_Derby_-_February_2019%29.webm"
curl -sL -A "$UA" -o p3.webm "$B/6/69/Goal_by_Rafael_Leao.webm"
for i in 0 1 2 3; do f=$(ls p$i.*); ffmpeg -v error -y -i $f -an -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,fps=25,setsar=1" -c:v libx264 -crf 23 n$i.mp4; done
printf "file n%d.mp4\n" 0 1 2 3 > l.txt; ffmpeg -v error -y -f concat -i l.txt -c copy ../videos/match.mp4
for i in 0 1 2 3; do ffprobe -v error -show_entries format=duration -of csv=p=0 n$i.mp4; done
