# Đề 12 – Xây dựng hệ thống tìm kiếm hình ảnh trong video: Khảo sát SOTA & đề xuất

*Cập nhật: 23/10/2026 (UTC+7). Ràng buộc: chỉ tài nguyên miễn phí (Colab/Kaggle, CPU box), không API trả phí, ưu tiên pretrained, xử lý theo lô. Môi trường đề bài (de_bai.pdf): Python 3.12, PyTorch 2.11, CUDA 13.2; "Ultralytics chưa hỗ trợ attention tốt"; xu hướng "smaller is better".*

Quy ước: **[ĐÃ XÁC MINH]** = đã mở trang nguồn trong phiên 23/10/2026. **[CHƯA XÁC MINH LẠI]** = nguồn kinh điển, link theo hiểu biết, chưa mở lại trong phiên này.

## 1. Bài toán
Đầu vào: ảnh truy vấn (cả cảnh) hoặc ảnh crop một đối tượng. Đầu ra: (video nguồn, đoạn start–end, thời điểm đỉnh, điểm). Tương ứng *Instance Search* (TRECVID INS) / *known-item search* (VBS) ở quy mô nhỏ.

## 2. Khảo sát

### 2.1 Bộ mã hoá ảnh
| Mô hình | Ghi chú | Nguồn |
|---|---|---|
| CLIP (OpenAI 2021) | Embedding toàn cục ảnh–văn bản; baseline chuẩn; ViT-B/32 chạy CPU | https://arxiv.org/abs/2103.00020 ; https://huggingface.co/openai/clip-vit-base-patch32 [CHƯA XÁC MINH LẠI] |
| OpenCLIP | Checkpoint LAION/DataComp mạnh hơn | https://github.com/mlfoundations/open_clip [CHƯA XÁC MINH LẠI] |
| SigLIP 2 (Google, 02/2025) | Hơn SigLIP ở mọi kích thước; cải thiện localization/dense; đa ngôn ngữ; NaFlex; B(86M)/L/So400m/g(1B) | https://arxiv.org/abs/2502.14786 ; https://huggingface.co/docs/transformers/main/en/model_doc/siglip2 [ĐÃ XÁC MINH] |
| DINOv2 (Meta 2023) | Self-supervised, mạnh cho instance retrieval; không gated | https://arxiv.org/abs/2304.07193 ; https://github.com/facebookresearch/dinov2 [CHƯA XÁC MINH LẠI] |
| DINOv3 (Meta, 08/2025) | Gram anchoring, dense feature SOTA, có ViT-S/16 nhỏ. **DINOv3 License** (không phải Apache): cho phép thương mại, phải kèm license + "Built with DINOv3" khi phân phối, ghi nhận khi công bố. **Trọng số HF gated: cần tài khoản HF, chấp nhận license (duyệt có thể vài ngày), HF token** | https://arxiv.org/abs/2508.10104 ; https://github.com/facebookresearch/dinov3 ; https://ai.meta.com/resources/models-and-libraries/dinov3-license/ ; https://github.com/facebookresearch/dinov3/issues/108 [ĐÃ XÁC MINH] |
| EmbeddingGemma 2 (Google DeepMind, 10/2026) | **Có tồn tại.** Đa phương thức text/ảnh/video/audio → 768-d; 740M (text 270M + vision 170M + audio 300M), nạp theo module (text+vision 440M); MRL 128–768; Apache 2.0; sentence-transformers. Hợp cho truy vấn văn bản→video; với ảnh→đúng vật thể chưa có số so với DINO → cần tự đo | https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2 ; https://developers.googleblog.com/en/embeddinggemma-2-the-developer-guide/ ; https://huggingface.co/google/embeddinggemma-2 [ĐÃ XÁC MINH; chưa kiểm HF gated hay không] |

### 2.2 Đề xuất vùng / đối tượng
| Công nghệ | Ghi chú | Nguồn |
|---|---|---|
| SAM 3 (Meta, 11/2025) | Detect+segment+track theo khái niệm (cụm danh từ hoặc **ảnh exemplar**) trên ảnh & video; 848M; cần CUDA ≥12.6, Python ≥3.12 | https://arxiv.org/abs/2511.16719 ; https://github.com/facebookresearch/sam3 ; https://ai.meta.com/research/sam3/ [ĐÃ XÁC MINH] |
| SAM 3.1 (27/03/2026) | Drop-in thay SAM 3; Object Multiplex (16 obj/forward), ~7× nhanh ở 128 obj (H100); checkpoint `facebook/sam3.1` (không có tích hợp Transformers; `build_sam3_predictor(version="sam3.1")`, cần HF auth). Commit release ghi ~31 FPS, ~17.7 GB bộ nhớ (H100, 5 obj, compiled) → **sát/vượt T4 16 GB** | https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md ; https://huggingface.co/facebook/sam3.1 ; https://github.com/facebookresearch/sam3/commit/f664253c90122f5d968a17c3f75a62893b4e15e7 ; https://ai.meta.com/blog/segment-anything-model-3/ [ĐÃ XÁC MINH]. Meta còn bán SAM 3.1 qua API trả phí (dev.meta.ai/models/sam-3-1) → **không dùng** |
| OWLv2 (NeurIPS 2023) | Open-vocab detector, có objectness và image-guided detection; trong Transformers; chạy T4 | https://arxiv.org/abs/2306.09683 [ĐÃ XÁC MINH] |
| Grounding DINO | Open-set detection theo text | https://arxiv.org/abs/2303.05499 [CHƯA XÁC MINH LẠI] |
| YOLO-World | Open-vocab realtime (qua Ultralytics — đề bài lưu ý hạn chế) | https://arxiv.org/abs/2401.17270 [CHƯA XÁC MINH LẠI] |
| Lưới đa tỉ lệ | Không cần detector, chạy CPU; baseline region trong mã | tự cài |

### 2.3 Keyframe, chỉ mục, re-ranking
- PySceneDetect: https://github.com/Breakthrough/PySceneDetect [CHƯA XÁC MINH LẠI]
- TransNet V2: https://arxiv.org/abs/2008.04838 ; https://github.com/soCzech/TransNetV2 [CHƯA XÁC MINH LẠI]
- FAISS: https://github.com/facebookresearch/faiss ; https://arxiv.org/abs/2401.08281 [CHƯA XÁC MINH LẠI] — Flat cho ≤ vài triệu vector; IVF-PQ/HNSW khi lớn.
- Re-ranking: αQE/DBA; k-reciprocal (https://arxiv.org/abs/1701.08398) [CHƯA XÁC MINH LẠI]; xác minh cục bộ bằng OWLv2 image-guided hoặc SAM 3.1 exemplar trên top-K khung; gộp hit theo thời gian (đã cài).

### 2.4 Hệ thống mã nguồn mở tương tự
- **DigUp** (MIT, 10/2026; EmbeddingGemma 2 qua llama.cpp; khung mỗi vài giây + 1 khung/shot; mở video tại thời điểm khớp): https://github.com/ARahim3/DigUp [ĐÃ XÁC MINH]. *Đánh giá riêng ở `digup_eval/`, không lặp lại.*
- MaterialSearch (GPLv3, CLIP): https://github.com/chn-lee-yumi/MaterialSearch [ĐÃ XÁC MINH]
- VideoSeek (ONNX+Lance+FFmpeg, tìm bằng screenshot): https://github.com/6v17/VideoSeek [ĐÃ XÁC MINH]
- catalogy (Rust, CLIP ViT-H-14 + LanceDB): https://github.com/bryantinsley/catalogy [ĐÃ XÁC MINH]

### 2.5 Dataset
| Dataset | Dùng được? | Nguồn |
|---|---|---|
| TRECVID INS (BBC EastEnders) | **Không**: BBC chấm dứt license video; chỉ còn query/GT | https://trecvid.nist.gov/past.data.table.html [ĐÃ XÁC MINH] |
| V3C1–3 (VBS) | Khó: 8.7 TB, ký data agreement NIST, không có GT instance | https://videobrowsershowdown.org/about-vbs/existing-data-and-tools/ ; https://arxiv.org/abs/1810.04401 [ĐÃ XÁC MINH] |
| **DAVIS 2017 trainval 480p** | **Chọn**: mask từng đối tượng/khung → GT thời gian; 833 MB; annotation **CC BY 4.0** (nguồn video gốc trong SOURCES.md của gói) | https://davischallenge.org/davis2017/code.html ; https://davischallenge.org/challenge2017/rulesdates.html [ĐÃ XÁC MINH] |
| LaSOT | Mở rộng (video dài, box mỗi khung, tải theo lớp 1–5 GB); **license không ghi rõ trên trang tải** | http://vision.cs.stonybrook.edu/~lasot/download.html [ĐÃ XÁC MINH trang] |
| YouTube-VOS / MOSE | Mở rộng | [CHƯA XÁC MINH] |
| Sintel (Blender, CC BY 3.0) | Demo định tính, không GT | https://durian.blender.org/sharing/ [ĐÃ XÁC MINH] |

## 3. Đánh giá theo ràng buộc & so sánh với hướng SAM 3.1 + DINOv3
- Dùng ngay: CLIP B/32 (baseline), DINOv2 (instance), SigLIP 2 (nếu cần truy vấn văn bản), FAISS Flat, gộp đoạn, DAVIS 2017.
- Cần HF token: DINOv3, SAM 3/3.1. Không khả thi: video TRECVID INS, V3C, API trả phí.

| | Kế hoạch này | SAM 3.1 + DINOv3 |
|---|---|---|
| Region | Lưới (CPU) → OWLv2 objectness (T4) | SAM 3.1 exemplar segment+track cả video |
| Embedding | DINOv2-small / CLIP → DINOv3 khi có token (cùng giao diện `Embedder`) | DINOv3 trên mask/crop |
| Chi phí | Chạy CPU box & T4 | 848M + ~17.7 GB (H100) → khó trên T4 với video dài; cả hai gated |
| Lợi thế bên kia | — | Mask chính xác + track → đoạn thời gian chính xác, ID đối tượng |
| Quyết định | Dùng SAM 3.1 ở bước **re-rank/xác minh** top-K đoạn (ít khung) thay vì index toàn bộ; DINOv3 thay DINOv2 khi có token | |

## 4. Pipeline
**Baseline**: mẫu đều 1 fps → CLIP ViT-B/32 toàn khung → FAISS IndexFlatIP → gộp hit cách nhau ≤1.5 s thành đoạn.
**Cải tiến**: (1) keyframe theo shot + mẫu đều; (2) index thêm vector vùng (grid → OWLv2/SAM 3); (3) encoder instance DINOv2/DINOv3; (4) truy vấn `both` = max(frame, region) theo (video, t); (5) re-rank top-K (αQE / SAM 3.1 exemplar).

## 5. Giao thức đánh giá (`scripts/prepare_davis.py`, `scripts/evaluate.py`)
- DAVIS 2017 **val** (30 sequence) → ghép 3 sequence/video → 10 mp4 24 fps (~124 s tổng). 12 khung đầu mỗi sequence **không đưa vào video**; khung 0 làm truy vấn → không rò rỉ.
- Truy vấn *object*: crop bbox mask (+15%) mỗi đối tượng (58). *Scene*: cả khung (30).
- GT: đoạn đối tượng xuất hiện (mask >200 px) / đoạn sequence phát. Đoạn trả về đúng nếu cùng video và chồng lấn GT ±0.5 s, mỗi GT khớp 1 lần.
- Chỉ số: Recall@1/5/10, mAP@10, ms/truy vấn, tốc độ index.
- Hạn chế: mỗi đối tượng chỉ có trong 1 sequence (truy vấn cùng cảnh, khác thời điểm) → dễ hơn thực tế; nên thêm truy vấn khác góc/khác nguồn.

## 6. Công nghệ đã chọn (bản chạy trên box)
| Thành phần | Phiên bản / checkpoint | Lý do | Nguồn |
|---|---|---|---|
| Python | 3.13.5 (box); mã tương thích 3.12 theo đề | | https://www.python.org |
| PyTorch | 2.14.1+cpu (box) | có sẵn | https://pytorch.org |
| Transformers | 5.20.2 | một giao diện cho CLIP/DINOv2/SigLIP2/OWLv2 | https://github.com/huggingface/transformers |
| faiss-cpu | 1.15.1 | chỉ mục vector | https://github.com/facebookresearch/faiss |
| opencv-python-headless | 5.0.0.93 | đọc/ghi video | https://github.com/opencv/opencv-python |
| Gradio | 6.30.0 | demo UI | https://github.com/gradio-app/gradio |
| Baseline encoder | `openai/clip-vit-base-patch32` | baseline chuẩn, nhẹ | https://huggingface.co/openai/clip-vit-base-patch32 |
| **Instance encoder (chính)** | `facebook/dinov3-vits16-pretrain-lvd1689m` (CLS ⊕ mean patch bỏ 4 register token, 768-d; tiền xử lý 224×224 ImageNet mean/std tự viết vì DINOv3ViTImageProcessor cần torchvision) | dense/instance feature SOTA, nhỏ chạy CPU; quyền HF đã được cấp | https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m ; https://github.com/facebookresearch/dinov3 |
| Instance encoder (so sánh) | `facebook/dinov2-small` | stand-in không gated | https://huggingface.co/facebook/dinov2-small |
| Region (SAM 3/3.1) | repo facebookresearch/sam3 commit 7f473cf (14/10/2026), checkpoint `facebook/sam3` (detector ảnh) / `facebook/sam3.1` (video multiplex); torchvision 0.29.1+cpu, timm, triton, pycocotools | phân đoạn theo khái niệm/exemplar | https://github.com/facebookresearch/sam3 |
| Region CPU | lưới 2×2 + 3×3, overlap 25% (13 vùng/khung) | không cần GPU | tự cài |
| Region GPU (tùy chọn, chưa test) | `google/owlv2-base-patch16-ensemble`, objectness top-8 | open-vocab, có trong Transformers | https://arxiv.org/abs/2306.09683 |
| Dataset | DAVIS 2017 trainval 480p (CC BY 4.0) | GT thời gian từ mask; nhỏ | https://davischallenge.org/davis2017/code.html |

**Thay đổi công nghệ**: (1) bỏ open_clip_torch (xung đột torchvision) → CLIP qua Transformers. (2) DINOv3 lúc đầu 403 → dùng DINOv2-small làm stand-in; sau khi được cấp quyền chuyển sang DINOv3 ViT-S/16 làm encoder chính, DINOv2 giữ để so sánh. (3) SAM 3 cài được trên CPU (vá device) nhưng OOM trên box → region trên CPU dùng lưới đa tỉ lệ; SAM 3/3.1 chuyển sang GPU Kaggle/Colab. (4) Mượn từ DigUp: lọc trùng aHash (`--dedup`), đoạn thời gian theo khung.

## 7. Kết quả
Xem `results/RESULTS.md` (số thật, CPU box).
