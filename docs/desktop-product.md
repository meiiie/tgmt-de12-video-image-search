# FrameAtlas desktop

## Product contract

FrameAtlas helps editors, researchers and people with local video archives find an exact moment, inspect it, save it and export it without uploading source media. Windows desktop is the release target verified here. Text and image retrieval use EG2; speech transcription and document search are outside this release.

The user authorized autonomous product and technical choices and explicitly prohibited subagents. The main agent performs implementation and review. Working name: FrameAtlas.

## Decisions

- Tauri 2 + React/TypeScript provides a native window, file dialogs, drag/drop and lifecycle management.
- A persistent local Python worker owns EG2, SQLite, decoding and search. PyTorch and NumPy perform numerical work in native libraries. Desktop retrieval scores a cached contiguous matrix exactly; the research CLI retains FAISS. Keeping model memory warm matters more than replacing orchestration with Go.
- SQLite WAL stores library paths, file fingerprints, per-frame embeddings, job checkpoints, settings and saved moments. Source files are never moved or deleted.
- A single inference lock avoids concurrent model memory spikes. Indexing yields between batches; search reuses a bounded embedding cache. Full 768-d normalized vectors are stored as FP32. GPU inference uses BF16 only when supported, otherwise FP32. FP16 is rejected: the model card documents an activation-range failure. Images keep their aspect ratio; the default 140-token vision budget matches EG2's video default. Users can select 70 or 280 tokens with an explicit rebuild.
- Only EG2 text and vision encoders are loaded. Audio is not part of the initial product.
- Import is explicit. Folder refresh discovers new/changed videos. Completed batches persist, restarts resume unfinished files, pause/cancel/retry are visible states.
- The worker binds loopback only, uses a random per-run token, restricts CORS, and serves media by database ID. No arbitrary unauthenticated filesystem endpoint.
- Desktop bundles its Python runtime and engine dependencies. EG2 downloads from the official pinned revision during setup; existing local model folders can be selected. Offline search works after setup.
- Python 3.14.10 is extracted from the official embeddable archive with its published SHA-256 verified. No system Python installation is required. A single-instance guard prevents two UI processes sharing a worker/database, and a Windows job object owns the worker's process tree.
- Occurrence search is an explicit control within one selected video. Ordinary queries retain words such as “last night”; the application does not silently treat them as temporal commands. An unavailable nth event returns no result.

Alternatives considered: Electron would add a second browser runtime; all-Rust/Go inference would introduce a new model implementation before parity measurements; a hosted web app would weaken offline and local-file workflows. Tauri with a persistent EG2 worker retains the verified model ecosystem and native desktop controls.

## Primary-source research

- [DigUp](https://github.com/ARahim3/DigUp): local folder selection, background indexing and results that open at the matching moment. Adopt the workflow, not its whole implementation.
- [Immich FAQ](https://docs.immich.app/FAQ/): separate media-library concerns from machine-learning jobs. This project does not need Immich's server deployment topology.
- [LosslessCut](https://github.com/mifi/lossless-cut): timestamps, markers and export make retrieval useful in an editing workflow. Accurate re-encoded clip export is the default here; no claim of keyframe-independent lossless cuts.
- [EG2 model card](https://huggingface.co/google/embeddinggemma-2): text+vision can omit the audio encoder; use SearchQuery for text and normalized embeddings. Pin revision `f9972ac22e696a105c482202646979e33e4b5a1e`.
- [Tauri sidecars](https://v2.tauri.app/develop/sidecar/): native shell can own a separately packaged computation process.

## Acceptance

The Windows binary launches without a console or a manually started Python server. A fresh library supports model setup, explicit video/folder import, persistent progress, pause/resume, retry, removal of catalog entries without deleting originals, text/image retrieval, actual video playback at the selected moment, saved moments, and clip export. Restart preserves the catalog and recovers unfinished jobs. Automated checks cover persistence, isolation, invalid media, ranking and cancellation. Real EG2 and desktop interaction checks are recorded separately from unit fixtures.

## Visual lab

`lab/desktop-concept-v1.png` was generated with the built-in imagegen tool. It explores an ivory workspace, dark navigation rail, ochre selection and an adjacent video inspector. Illustrative metadata, confidence percentages and captions in the image are not product functionality. The implemented app uses actual library data and raw similarity, with accessible controls and reduced-motion support.
