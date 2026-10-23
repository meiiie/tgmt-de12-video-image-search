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


## Built with DINOv3
Dự án này dùng DINOv3 (`facebook/dinov3-vits16-pretrain-lvd1689m`) của Meta, phát hành theo **DINOv3 License** (https://ai.meta.com/resources/models-and-libraries/dinov3-license/), không phải giấy phép mã nguồn mở thông thường: được dùng/sửa/phân phối (kể cả thương mại) nhưng khi phân phối trọng số hoặc sản phẩm phái sinh phải kèm bản license và ghi rõ "Built with DINOv3"; công bố kết quả phải ghi nhận việc dùng DINOv3; tuân thủ điều khoản kiểm soát thương mại. Repo này không phân phối trọng số DINOv3 (tải từ Hugging Face sau khi được Meta cấp quyền). Paper: https://arxiv.org/abs/2508.10104
