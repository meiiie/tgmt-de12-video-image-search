# Kaggle kernel `holilihu/tgmt-de12-video-image-search`
- Private, GPU T4 (`NvidiaTeslaT4`; P100 bị CLI báo đã retired), internet bật (tải DAVIS + clone repo sam3, KHÔNG tải trọng số HF).
- Trọng số: dataset private `holilihu/de7-weights` (dataset_sources) → `/kaggle/input/de7-weights`: `dinov3-vits16-pretrain-lvd1689m__*` (ghép lại thành thư mục HF bằng symlink), `sam31_part_00..11` (+`sam31_sha256.txt`) ghép thành `sam3.1_multiplex.pt` và kiểm sha256. `vsearch/weights.py` tự dò layout (cả thư mục HF lẫn file checkpoint thô), log vào `results/weights_layout.json`.
- Không dùng Kaggle Secrets / HF_TOKEN. Thiếu trọng số → `results/STATUS.txt` và dừng.
- SAM 3.1: dùng phần `detector.*` của checkpoint multiplex cho image detector (số key thiếu/thừa được ghi trong `gpu_bench.json`).
- Push: `kaggle kernels push -p kaggle/ -t 7000`
