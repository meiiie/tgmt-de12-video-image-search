# Kết quả thực nghiệm (số đo thật, box CPU, 23/10/2026 UTC+7)

**Benchmark**: DAVIS 2017 val, 30 sequence → 10 video mp4 (24 fps, 854×480, ~68 s tổng), lấy mẫu 1 fps = 73 khung. Region = lưới 2×2+3×3 (13 vùng/khung) → 1022 vector/index. Query frame không nằm trong index. FAISS IndexFlatIP. Gộp đoạn: hit cùng video cách ≤1.5 s.
Bộ truy vấn: `object` (58 crop đối tượng), `object_small` (35 crop có mask <5% khung), `object_hard` (58 crop lật + thu 50% + tối 0.7 + dán lên nền nhiễu), `scene` (30 khung đầy đủ).
`top1_peak_in_GT` = thời điểm đỉnh của kết quả top-1 nằm trong đoạn đối tượng xuất hiện.

## Truy vấn khó (object_hard, n=58) – bảng chính
| Encoder | Index | R@1 | R@5 | mAP@10 | top1 peak∈GT |
|---|---|---|---|---|---|
| CLIP ViT-B/32 (baseline) | frame | 0.534 | 0.793 | 0.659 | 0.431 |
| CLIP ViT-B/32 | region | 0.293 | 0.707 | 0.475 | 0.241 |
| CLIP ViT-B/32 | both | 0.293 | 0.741 | 0.478 | 0.241 |
| DINOv2-small (stand-in) | frame | 0.759 | 0.983 | 0.848 | 0.759 |
| DINOv2-small | region | 0.759 | 0.983 | 0.807 | 0.724 |
| DINOv2-small | both | 0.759 | 0.983 | 0.813 | 0.724 |
| **DINOv3 ViT-S/16** | frame | 0.724 | 0.983 | 0.814 | 0.707 |
| **DINOv3 ViT-S/16** | region | 0.759 | 0.966 | 0.832 | 0.759 |
| **DINOv3 ViT-S/16** | **both** | **0.776** | 0.966 | **0.844** | **0.776** |

## Đối tượng nhỏ (object_small, n=35)
| Encoder | frame R@1 / mAP | region R@1 / mAP | both R@1 / mAP |
|---|---|---|---|
| CLIP B/32 | 0.886 / 0.921 | 0.829 / 0.898 | 0.829 / 0.898 |
| DINOv2-small | 0.943 / 0.971 | 0.971 / 0.986 | 0.971 / 0.986 |
| DINOv3 ViT-S/16 | 0.971 / 0.986 | 1.000 / 1.000 | 1.000 / 1.000 |

## Bộ dễ (crop gốc / cả khung)
| Encoder | Query | frame R@1 / mAP | region R@1 / mAP | both R@1 / mAP |
|---|---|---|---|---|
| CLIP B/32 | object (58) | 0.931 / 0.932 | 0.897 / 0.919 | 0.897 / 0.919 |
| CLIP B/32 | scene (30) | 0.967 / 0.983 | 1.000 / 1.000 | 1.000 / 1.000 |
| DINOv2-small | object (58) | 0.966 / 0.963 | 0.983 / 0.971 | 0.983 / 0.971 |
| DINOv2-small | scene (30) | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| DINOv3 ViT-S/16 | object (58) | 0.983 / 0.971 | 1.000 / 0.980 | 1.000 / 0.980 |
| DINOv3 ViT-S/16 | scene (30) | 0.967 / 0.983 | 1.000 / 1.000 | 1.000 / 1.000 |
R@10 = 1.0 ở mọi cấu hình vì chỉ có 10 video → chỉ số này bão hoà, không dùng để so sánh.

## Tốc độ (CPU 8 lõi dùng chung, load average 24–38 do agent khác → số chậm hơn thực tế nhiều)
| Encoder | Index 73 khung × 14 crop | khung/s | ms/truy vấn (embed+search) |
|---|---|---|---|
| CLIP B/32 | 265 s | 0.28 | 930–7200 |
| DINOv2-small | 225 s | 0.33 | 3200–5800 |
| DINOv3 ViT-S/16 | 944 s (chạy song song với probe SAM 3) | 0.08 | 6100–10700 |
Phần FAISS search + merge chiếm < vài ms; gần như toàn bộ là thời gian embed ảnh truy vấn trên CPU bị tranh chấp. Cần đo lại trên GPU T4 (notebook).

## SAM 3 / 3.1
- Cài được repo sam3 (commit 7f473cf, 14/10/2026) trên CPU sau khi vá `device="cuda"` hard-code (scripts/sam3_cpu.patch) và cài torchvision 0.29.1+cpu, triton, pycocotools, psutil.
- **Chạy thử trên box bị OOM-kill** (RSS ~7.2 GB khi nạp model, box chỉ còn ~8 GB trống dùng chung) → **chưa có số đo SAM 3 region**. Cần Kaggle/Colab GPU (cell trong notebook).

## Nhận xét
1. DINOv3 + index region (`both`) tốt nhất trên bộ khó: R@1 0.776 / mAP 0.844, so với baseline CLIP frame 0.534 / 0.659 (+24 điểm R@1).
2. Với CLIP, crop vùng lưới **làm giảm** kết quả (embedding toàn cục bị nhiễu bởi crop cắt ngang); với DINO thì region giúp ở đối tượng nhỏ và bộ khó → chọn DINO cho region.
3. Benchmark DAVIS còn dễ (cùng cảnh, ít video); cần thêm distractor/khác góc để phân biệt rõ hơn.


## Bộ lớn: 70 video (10 video val + 60 video distractor DAVIS 2017 train), 276 khung @1 fps
Cùng 58 truy vấn; distractor không chứa đối tượng truy vấn. R@10 không còn bão hoà nhưng theo yêu cầu chỉ báo R@1, mAP@10.
| Cấu hình | object_hard R@1 | object_hard mAP@10 | object R@1 | object mAP@10 |
|---|---|---|---|---|
| CLIP B/32 frame (baseline) | 0.190 | 0.298 | 0.862 | 0.876 |
| DINOv3-S/16 frame | 0.552 | 0.644 | 0.862 | 0.907 |
| DINOv3-S/16 region (grid) | 0.586 | 0.680 | 0.966 | 0.957 |
| **DINOv3-S/16 frame+region** | **0.586** | **0.680** | **0.966** | **0.957** |
Index (CPU box dùng chung, load ~26): CLIP frame 276 vector 1305 s; DINOv3 frame+grid 3864 vector 1237 s (~0.22 khung/s). Truy vấn: CLIP 138–1593 ms, DINOv3 127–220 ms (embed + FAISS + merge).
Distractor licenses: results/licenses_distractors.md. SAM 3 region / re-rank trên bộ này: chưa chạy (cần GPU – kaggle/).

## Built with DINOv3
Dự án này dùng DINOv3 (`facebook/dinov3-vits16-pretrain-lvd1689m`) của Meta, phát hành theo **DINOv3 License** (https://ai.meta.com/resources/models-and-libraries/dinov3-license/), không phải giấy phép mã nguồn mở thông thường: được dùng/sửa/phân phối (kể cả thương mại) nhưng khi phân phối trọng số hoặc sản phẩm phái sinh phải kèm bản license và ghi rõ "Built with DINOv3"; công bố kết quả phải ghi nhận việc dùng DINOv3; tuân thủ điều khoản kiểm soát thương mại. Repo này không phân phối trọng số DINOv3 (tải từ Hugging Face sau khi được Meta cấp quyền). Paper: https://arxiv.org/abs/2508.10104

## Kaggle GPU v2 (T4, fp16 autocast) — 26/10/2026, kernel v2 holilihu/tgmt-de12-video-image-search
Nguồn: `results/kaggle_v2_de12_results.json` (1 file, 0 lỗi stage). Benchmark 70 video (276 frame @1 fps), 58 truy vấn/bộ. torch 2.11.0+cu128.

| Bộ truy vấn | Cách | R@1 | mAP@10 | ms/truy vấn |
|---|---|---|---|---|
| hard | DINOv3 frame | 0.552 | 0.642 | 27.3 |
| hard | DINOv3 region grid | 0.586 | 0.679 | 28.3 |
| hard | DINOv3 frame+grid | 0.586 | 0.680 | 28.9 |
| hard | DINOv3 region SAM 3.1 | 0.000 | 0.000 | 27.0 |
| hard | frame+grid + SAM 3.1 re-rank top-20 | 0.586 | 0.680 | 24653 |
| plain | DINOv3 frame | 0.862 | 0.907 | 28.3 |
| plain | DINOv3 region grid / frame+grid | 0.966 | 0.957 | 29.2 / 29.8 |
| plain | DINOv3 region SAM 3.1 | 0.000 | 0.000 | 28.4 |
| plain | frame+grid + SAM 3.1 re-rank top-20 | 0.966 | 0.957 | 24657 |

GPU: DINOv3 ViT-S/16 132.8 ảnh/s, VRAM đỉnh 0.25 GB; index grid 9.65 frame/s (3864 vector). SAM 3.1: nạp 17.4 s, 1.038 s/frame, VRAM đỉnh 3.79 GB, **0.0 box/frame** (prompt "object", ngưỡng 0.3); index SAM chỉ 281 vector / 276 frame. Nạp `detector.*` từ sam3.1_multiplex: 1166 key, thiếu 4 (`backbone.vision_backbone.convs.3.*`), thừa 36.
**Kết luận:** SAM 3.1 (như đang nạp) gần như không trả về vùng nào, nên region SAM = 0 và re-rank không đổi kết quả so với grid; DINOv3 + grid vẫn tốt nhất (hard 0.586/0.680). Nghi do 4 key thiếu khi lấy detector từ checkpoint multiplex và/hoặc prompt chung "object"; cần thử checkpoint ảnh sam3.pt hoặc prompt/ngưỡng khác.

## Kaggle GPU v3 (T4, fp16) — 26/10/2026, kernel v3 — KẾT QUẢ CUỐI
Nguồn: `results/kaggle_v3_de12_results.json`. Chạy 21:57–22:07 (UTC+7). SAM 3 dùng checkpoint ảnh `sam3.pt` (facebook/sam3, sha256 9999e234…, dataset private `holilihu/de12-sam3-image`): **missing = 0**, unexpected = 22 (`backbone.vision_backbone.sam2_convs.*`, phần dành cho tracker SAM 2), 1156 key detector.
Kiểm tra nhanh 5 frame (prompt "object", ngưỡng 0.3): số box = [0, 0, 0, 0, 0] → bỏ qua các bước SAM như đã định. gpu_bench (39 frame): SAM 3 tốn 1.043 s/frame, VRAM đỉnh 3.79 GB, 0.0 box/frame; DINOv3 đạt 141.7 ảnh/s với VRAM 0.25 GB.

| Bộ | Truy vấn | frame R@1 / mAP@10 | grid region R@1 / mAP@10 | frame+grid R@1 / mAP@10 | ms/truy vấn (frame+grid) |
|---|---|---|---|---|---|
| 70 video | hard | 0.552 / 0.642 | 0.586 / 0.679 | 0.586 / 0.680 | 24.8 |
| 70 video | plain | 0.862 / 0.907 | 0.966 / 0.957 | 0.966 / 0.957 | 26.1 |
| 10 video | hard | 0.690 / 0.793 | 0.759 / 0.835 | 0.759 / 0.838 | 24.9 |
| 10 video | plain | 0.983 / 0.971 | 1.000 / 0.980 | 1.000 / 0.980 | 26.6 |

Lưu ý: trên GPU fp16, bộ 10 video hard đạt R@1 0.759, còn số 0.776 cũ đo trên CPU fp32. Nguyên nhân chênh lệch chưa được kiểm chứng.

## Ablation âm: SAM 3.1 / SAM 3 (quyết định cuối: DINOv3 + grid)
- v2: SAM 3.1 multiplex `detector.*` nạp được 1166 key, thiếu 4 (`convs.3.*`), thừa 36. Kết quả 0.0 box/frame; SAM region R@1 = 0.000; re-rank top-20 cho đúng kết quả của grid (hard 0.586 / 0.680) nhưng mất 24.7 s/truy vấn, chậm khoảng 850 lần.
- v3: SAM 3 `sam3.pt` nạp đủ, missing = 0, nhưng vẫn ra 0 box trên 5/5 frame. Như vậy lệch key **không** phải nguyên nhân chính. Giả thuyết chưa kiểm chứng: prompt chung "object" không phù hợp với detector theo khái niệm của SAM 3, cách đọc output/ngưỡng của `Sam3Processor`, hoặc fp16 autocast.
- Chi phí: SAM khoảng 1.04 s/frame và 3.8 GB VRAM. DINOv3 + grid chỉ cần khoảng 0.1 s/frame cho cả index và khoảng 25 ms/truy vấn.
- Kết luận: Đề 12 chốt **DINOv3 ViT-S/16 + region grid + FAISS** (Built with DINOv3). SAM được ghi nhận là ablation âm.

## Kaggle v4/v5 — hybrid DINOv3 + SAM 3 (27/10/2026)
- v4 (23:31–23:47 UTC+7, 26/10) **thất bại**. SAM chạy fp32 thuần thì crash: `mat1 and mat2 must have the same dtype (BFloat16 vs Float)`, vì repo có op bf16 bên trong. EG2 cũng không import được do xung đột torchvision. Số DINOv3 grid trong lần chạy này giống hệt v3 (`results/kaggle_v4_de12_results.json`).
- Nguyên nhân 0 box ở v2/v3 đã xác định trên CPU của box: prompt chung "object" chỉ đạt score 0.02–0.08. Ảnh mẫu chính thức truck.jpg với prompt "truck" đạt 0.863. Ngoài ra `Sam3Processor` mặc định `confidence_threshold=0.5`. Cách sửa: dùng bộ prompt theo lớp (person, animal, dog, horse, cow, bird, car, bicycle, motorcycle, boat, ball, vehicle), đặt threshold của processor là 0.0, tự lọc ở ≥0.3 rồi chạy NMS (IoU 0.7), giữ tối đa 8 box/frame. Vector vùng = DINOv3 của crop đã che bằng mask SAM (pixel ngoài mask tô xám).
- v5 (23:52 26/10 → 00:48 27/10 UTC+7, `results/kaggle_v5_de12_results.json`). Sanity với autocast fp16: truck đạt 0.865 (1 box), "object" đạt 0.075 (0 box); 5 frame DAVIS cho [5, 8, 6, 1, 8] box. Nạp sam3.pt: missing 0, unexpected 22. SAM: 2.633 s/frame, 4.36 box/frame, VRAM đỉnh 4.73 GB. Index grid+SAM: 0.35 frame/s, so với 10.3 frame/s khi chỉ dùng grid (70 video: 1104 box SAM, 4.0 box/frame).

| Bộ / truy vấn | frame+grid (mặc định) | chỉ vùng SAM | frame+SAM | frame+grid+SAM (fuse) | re-rank SAM top-20 |
|---|---|---|---|---|---|
| 70 video hard | 0.586 / 0.680 | 0.276 / 0.369 | 0.448 / 0.526 | 0.517 / 0.582 | **0.603 / 0.684** |
| 70 video plain | 0.966 / 0.957 | 0.776 / 0.815 | 0.897 / 0.922 | 0.948 / 0.948 | 0.966 / 0.957 |
| 10 video hard | 0.759 / 0.838 | 0.534 / 0.603 | 0.655 / 0.731 | 0.741 / 0.788 | 0.759 / 0.836 |
| 10 video plain | 1.000 / 0.980 | 0.897 / 0.882 | 0.966 / 0.960 | 0.983 / 0.971 | 1.000 / 0.980 |
(R@1 / mAP@10.) Thời gian truy vấn: khoảng 25–27 ms khi chỉ dùng index. Re-rank tốn 936.6 ms/truy vấn (70 video hard) và 517.5 ms (10 video hard). Phần re-rank dùng lại box SAM đã lưu lúc index (229 keyframe duy nhất, 4.04 box/keyframe), nên thời gian chủ yếu là đọc frame và embed crop. Nếu phải chạy SAM mới cho từng keyframe thì cần thêm khoảng 2.6 s/keyframe.
**Nhận xét:** re-rank SAM chỉ tăng R@1 trên 70 video hard từ 0.586 lên 0.603, tức thêm 1/58 truy vấn, kèm khoảng +0.9 s/truy vấn và chi phí index tăng khoảng 30 lần. Các bộ còn lại không đổi hoặc giảm. Vùng SAM thay cho grid thì kém hơn (vùng SAM theo lớp bỏ sót vật thể ngoài bộ prompt). Mặc định vẫn là DINOv3 + grid; re-rank SAM để làm tuỳ chọn.

## EmbeddingGemma 2 (google/embeddinggemma-2) — box CPU, chỉ frame, bộ 10 video (27/10/2026)
Nguồn: model card https://huggingface.co/google/embeddinggemma-2, blog https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/ (06/10/2026), tài liệu https://ai.google.dev/gemma/docs/embeddinggemma. Model đa phương thức (text/ảnh/video/âm thanh), 740M tham số, embedding 768 chiều, giấy phép Apache-2.0. Weights được đưa lên dataset private `holilihu/de12-embeddinggemma2`.
| Truy vấn | EG2 frame R@1 / mAP@10 | DINOv3 frame | DINOv3 frame+grid |
|---|---|---|---|
| 10 video hard | **0.983 / 0.971** (1379 ms/truy vấn, CPU) | 0.690 / 0.793 | 0.759 / 0.838 |
| 10 video plain | **0.983 / 0.971** (2324 ms/truy vấn, CPU) | 0.983 / 0.971 | 1.000 / 0.980 |
Đã kiểm tra rò rỉ: không thấy (notes/eg2_leakage_audit.md). Bộ 70 video chưa có số: cần kernel v6 (sentence-transformers==6.2.0); v5 hỏng vì `Pooling.__init__() missing 'embedding_dimension'` do bản sentence-transformers mới hơn.

## Kaggle T4 v7 (27/10/2026): EmbeddingGemma 2 vs DINOv3, cùng một lần chạy
Nguồn: `results/kaggle_v7_de12_results.json`. Kernel v7 chạy 49 phút (03:40–04:30 UTC+7). EG2 dùng fp32, ảnh resize 224, `sentence-transformers` 6.2.0. Lỗi Pooling ở v5/v6 là do dataset làm phẳng `1_Pooling/config.json` thành `1_Poolingconfig.json`, không phải do phiên bản; v7 đã sửa đường dẫn.

| Bộ | Model / chế độ | R@1 | R@5 | R@10 | mAP@10 | ms/truy vấn | frame/s khi index |
|---|---|---|---|---|---|---|---|
| 70 video hard | DINOv3 frame+grid (`both`) | 0.586 | 0.828 | 0.931 | 0.680 | 24.5 | 10.0 |
| 70 video hard | **EG2 frame** | **0.948** | 1.000 | 1.000 | **0.951** | 477 | 2.02 |
| 70 video hard | EG2 frame+grid (`both`) | 0.810 | 0.948 | 0.966 | 0.842 | 509 | 0.15 |
| 70 video thường | DINOv3 frame+grid | 0.966 | 1.000 | 1.000 | 0.957 | 25.7 | 10.0 |
| 70 video thường | EG2 frame | 0.966 | 1.000 | 1.000 | 0.960 | 483 | 2.02 |
| 70 video thường | EG2 frame+grid | 1.000 | 1.000 | 1.000 | 0.980 | 508 | 0.15 |
| 10 video hard | DINOv3 frame+grid | 0.759 | 0.966 | 1.000 | 0.838 | 22.9 | 10.1 |
| 10 video hard | EG2 frame | 0.983 | 1.000 | 1.000 | 0.971 | 485 | 1.96 |

Quyết định: **EG2 chỉ frame là backbone mặc định** (thắng rõ trên 70 video hard). DINOv3 + grid vẫn chọn được (`--model facebook/dinov3-vits16-pretrain-lvd1689m --regions grid`), nhanh hơn khoảng 20 lần mỗi truy vấn. Lưới vùng làm EG2 kém đi trên bộ hard. SAM 3 re-rank vẫn là tuỳ chọn. Kết quả trên GPU khớp kết quả CPU trước đó trên 10 video (0.983/0.971). n=58 truy vấn, nên mỗi truy vấn tương đương 1.7 điểm R@1.

## v8 (27/10/2026): tăng tốc độ và độ chính xác cho EG2, đo trên 70 video hard và 10 video hard

Các con số dưới đây là số thật. Bộ truy vấn là `object_hard` với n = 58. Bộ 70 video có 276 khung hình, bộ 10 video có 73 khung, lấy mẫu 1 fps.

Cách đo:
- Kernel Kaggle v8 (T4, private) chạy từ 10:06 đến 10:48 (UTC+7), không lỗi. Nó dump toàn bộ embedding ra `results/kaggle_v8_de12_results.json`; phần base64 của embedding đã được bỏ khỏi file trong repo.
- Mọi thí nghiệm sau đó chạy offline trên box bằng `scripts/offline_v8.py`, cùng logic segment và metric như `evaluate.py`. Kết quả nằm ở `results/v8_offline.json`.
- Script này tái tạo đúng số của v7: DINOv3 0.586/0.680, EG2 0.948/0.951.
- Phần chạy trên CPU của box nằm ở `results/v8_box_tokens.json` và `results/v8_cpu_variants.json`. Box là máy dùng chung với agent khác nên thời gian đo trên CPU bị nhiễu; mình báo p50.

| Phương án | 70v R@1 | 70v mAP@10 | 10v R@1 | 10v mAP@10 | ms/truy vấn (encode query) |
|---|---|---|---|---|---|
| DINOv3 frame+grid (T4 fp16) | 0.586 | 0.680 | 0.759 | 0.838 | 16.5 |
| EG2 frame, fp32 (T4) – mặc định cũ | 0.948 | 0.951 | 0.983 | 0.971 | 461 (forward 457 + preprocess 7) |
| **EG2 frame, fp16 (T4), cả index và query – mặc định mới** | **0.948** | **0.951** | **0.983** | **0.971** | **203** (forward 180) |
| Late fusion z-score, w chọn trên 10v (w_EG2 = 1.0) | 0.948 | 0.951 | 0.983 | 0.971 | 461 + 16.5 |
| Late fusion RRF (k = 60), w chọn trên 10v (= 1.0) | 0.948 | 0.951 | 0.983 | 0.971 | 461 + 16.5 |
| Hai tầng: DINOv3 top-50 → EG2 | 0.914 | 0.917 | 0.983 | 0.971 | 461 + 16.5 |
| Hai tầng: DINOv3 top-100 / top-200 → EG2 | 0.948 | 0.951 | 0.983 | 0.971 | 461 + 16.5 |
| EG2 Matryoshka 512 / 256 / 128 chiều | 0.931 / 0.914 / 0.828 | 0.943 / 0.923 / 0.868 | 0.966 / 0.948 / 0.948 | 0.963 / 0.954 / 0.946 | không đổi (search < 0.03 ms) |
| SAM 3 re-rank top-20 của EG2, max(frame, crop) | 0.690 | 0.769 | 0.776 | 0.834 | + khoảng 2.7 s/khung nếu chạy SAM lúc truy vấn |
| SAM 3 re-rank top-20 của EG2, 0.5·frame + 0.5·max | 0.914 | 0.926 | 0.966 | 0.955 | như trên |
| CPU box: query fp32, index fp32 | 0.948 | 0.951 | 0.983 | 0.971 | 1928 (p50) |
| CPU box: query bf16, index fp32 | 0.948 | 0.951 | 0.983 | 0.971 | 487–640 (p50, hai lần chạy) |
| CPU box: query bf16 và index bf16 | 0.897 | 0.922 | 0.983 | 0.971 | 487 |
| CPU box: token ảnh 140 / 70 (mặc định 280), bf16 | 0.897 / 0.793 | 0.922 / 0.855 | 0.983 / 0.931 | 0.971 / 0.937 | 386 / 267 |
| CPU box: torch dynamic int8 cho Linear (trừ input_proj), chỉ đo 10v | – | – | 0.621 | 0.760 | 1128 |
| CPU box: ONNX Runtime fp32 (export bằng dynamo), chỉ đo tốc độ | – | – | – | – | 5919 |

Tầng 1 của phương án hai tầng là DINOv3 lấy top-K khung. Recall@K của tầng này (có ít nhất một khung GT trong top-K) trên 70 video:

| K | 10 | 20 | 50 | 100 | 200 |
|---|---|---|---|---|---|
| Recall@K | 0.828 | 0.897 | 0.966 | 1.000 | 1.000 |

Trên 10 video, recall@50 đạt 1.000.

Kết luận:
1. **Chỗ chậm là encode ảnh query.** Bước này chiếm hơn 99% thời gian: forward 457 ms, preprocess 7 ms, còn search FAISS flat chỉ khoảng 0.02 ms vì kho có 276 vector. Vì vậy FAISS HNSW, tầng 1 hai tầng và Matryoshka hầu như không giúp tốc độ. Matryoshka chỉ giảm dung lượng index, và với 256 chiều thì R@1 trên 70 video mất 0.034.
2. **fp16 trên GPU là lựa chọn thắng rõ.** Độ chính xác giữ nguyên (cosine giữa query fp16 và fp32 là 1.000), query nhanh hơn 2.3 lần (461 → 203 ms), index nhanh hơn 2.4 lần (2.16 → 5.26 khung/s). Vì vậy app giờ mặc định EG2 fp16 khi chạy trên CUDA và fp32 khi chạy trên CPU; có thể đổi qua biến `DE12_EG2_DTYPE`.
3. **Late fusion không giúp.** Trên 10 video, w tốt nhất là 1.0, tức chỉ dùng EG2. Trên 70 video, mọi w < 0.9 đều làm điểm kém đi.
4. **Hai tầng không có lợi.** Phương án này không nhanh hơn vì vẫn phải encode query bằng EG2, và với K ≤ 50 thì độ chính xác còn giảm.
5. **SAM 3 re-rank làm EG2 kém đi.** SAM tìm được 4.0 box/khung (1104 box trên 276 khung, 2.71 s/khung trên T4). Crop nền gây match sai. Vì vậy SAM 3 không được dùng với EG2.
6. **Trên CPU, nên dùng query bf16 với index fp32.** Cách này nhanh hơn khoảng 3 lần mà không mất độ chính xác. Mình chưa đổi mặc định cho CPU vì thời gian đo trên box bị nhiễu do máy dùng chung. int8 dynamic, ONNX và giảm token ảnh đều tệ hơn hoặc chậm hơn. Lần chạy ONNX int8 bị dừng giữa chừng nên chưa có số.

Công nghệ và nguồn:
- EmbeddingGemma 2 qua sentence-transformers 6.2.0 và transformers 5.20.2: [model card](https://huggingface.co/google/embeddinggemma-2), [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/). Thông tin "hỗ trợ Matryoshka 768/512/256/128" lấy từ model card và [tài liệu Gemma](https://ai.google.dev/gemma/docs/embeddinggemma); mình chưa đọc lại để xác minh lần này nên đánh dấu là chưa xác minh.
- Tham số `max_soft_tokens` = 280 đọc từ `processor_config.json` của model.
- DINOv3 vits16.
- SAM 3 (`sam3.pt`, repo facebookresearch/sam3).
- FAISS (IndexFlatIP, IndexHNSWFlat).
- PyTorch `quantize_dynamic`.
- `torch.onnx` (dynamo) cùng ONNX Runtime 1.31.1.
- RRF theo Cormack et al., SIGIR 2009 (chưa xác minh link trong lần này).
