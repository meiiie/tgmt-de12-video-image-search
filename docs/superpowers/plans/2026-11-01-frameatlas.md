# FrameAtlas implementation plan

Main agent executes and reviews every step directly. No subagents.

Goal: a usable Windows video-search desktop application built around EG2.
Spec: `docs/desktop-product.md`.

- [x] Fix temporal baseline defects and verify existing audit.
- [x] Implement persistent library, resumable jobs, EG2 lifetime, exact retrieval, media and exports in `desktop/backend/`.
- [x] Add behavioral tests for persistence, duplicates, interruption, search, validation and authenticated APIs.
- [x] Build the real React desktop UI and visual lab, with native import, settings, activity and saved moments.
- [x] Implement Tauri worker lifecycle, connection bootstrap, native dialogs and reveal-in-folder.
- [x] Exercise real EG2, record CPU timing separately from correctness and verify image/text paths.
- [x] Package a portable Windows application and verify the extracted runtime, actual EG2 and export loop.
- [x] Review the complete diff, fix failures, document operation and remaining limits with evidence.

Delivery adjustment: the verified portable ZIP is the usable release artifact for this pass. NSIS compilation of the full runtime was stopped after prolonged packaging and remains unfinished. Native file-dialog interaction was not repeated after the user requested that all UI work stay in the Codex side panel. See `docs/desktop-verification.md` for the exact verification boundary.

Primary review cases: missing/moved files; cancellation during inference; changed source/model configuration; loopback auth and path handling; restart with partial state; video formats unsupported by the webview; exhausted memory or disk. Do not replace real acceptance with fixture results.
