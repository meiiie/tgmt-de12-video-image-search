# Football demo clips (Wikimedia Commons), joined in this order into match.mp4 by scripts/get_soccer_demo.sh

| # | match.mp4 time | Commons file | Author | Licence |
|---|---|---|---|---|
| 0 | 0.00–35.60 s | [Saša Viciknez 2006 CSL quarterfinal goal.ogv](https://commons.wikimedia.org/wiki/File:Sa%C5%A1a_Viciknez_2006_CSL_quarterfinal_goal.ogv) | Djuradj Vujcic | CC BY 2.0 |
| 1 | 35.60–49.12 s | [Sidemen Charity Match 2025 - Sketch Save.webm](https://commons.wikimedia.org/wiki/File:Sidemen_Charity_Match_2025_-_Sketch_Save.webm) | Celsoazevedo | CC BY 4.0 |
| 2 | 49.12–63.12 s | [Kaldırım scored the goal for a 3-3 draw (Beşiktaş-Fenerbahçe Derby - February 2019).webm](https://commons.wikimedia.org/wiki/File:Kald%C4%B1r%C4%B1m_scored_the_goal_for_a_3-3_draw_(Be%C5%9Fikta%C5%9F-Fenerbah%C3%A7e_Derby_-_February_2019).webm) | beIN SPORTS Türkiye | CC BY 3.0 |
| 3 | 63.12–66.52 s | [Goal by Rafael Leao.webm](https://commons.wikimedia.org/wiki/File:Goal_by_Rafael_Leao.webm) | Saggittarius A | CC BY-SA 4.0 |

Licence and author read from the Commons API (`extmetadata` LicenseShortName / Artist) on 27/10/2026. Modifications: rescaled to
640x360 letterbox, 25 fps, audio removed, concatenated. The derived video is not committed. The CC BY-SA 4.0 clip means a
redistributed match.mp4 must itself be CC BY-SA 4.0.

Ground-truth spans (eval_text/soccer_queries.json) were annotated by hand by looking at 2–4 fps contact sheets, so they are
approximate (about ±0.5 s): goal A 5.0–8.0 (shot into net), celebration A 9.5–30.0, keeper save 43.1–45.6, goal B 51.62–53.62,
celebration B 53.87–57.62, replay of goal B 58.12–63.12, goal C 64.62–66.52 (the clip ends as the ball goes in).
SoccerNet was not used: its videos require signing an NDA (https://www.soccer-net.org/data).
