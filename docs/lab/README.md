# FrameAtlas interface lab

The built-in `imagegen` skill/tool produced [desktop-concept-v1.png](desktop-concept-v1.png). The exact final prompt is recorded in [imagegen-prompt.txt](imagegen-prompt.txt). This is illustrative visual research, not a screenshot of functioning software.

The implemented React interface uses the concept's ivory workspace, dark navigation, restrained ochre accent, actual video thumbnails and an adjacent inspector. It replaces generated confidence percentages/captions with source filenames, real timestamps and raw cosine similarity. No model-generated image is used as a real search result.

The working lab is the actual application: `cd desktop; npm run tauri -- dev`. Reproducible UI fixtures and screenshots are produced by `npm run test:ui`; the report is in ignored `desktop/playwright-report/`, and screenshots in `outputs/onboarding/ui-*.png`.

Review criteria: clear first-run/empty states; search without interrupting indexing; readable source paths and progress; usable playback/seek; precise segment editing; recoverable errors; native file selection; keyboard focus; no horizontal overflow at 920×700. Automated WCAG AA checks cover the search screen, with manual native checks recorded separately.
