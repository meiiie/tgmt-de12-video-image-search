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
