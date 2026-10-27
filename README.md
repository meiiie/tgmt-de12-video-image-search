# Đề 12 – Tìm kiếm ảnh / đối tượng trong video (EmbeddingGemma 2 mặc định, DINOv3 + grid tuỳ chọn, FAISS, SAM 3 re-rank)

Đầu vào là **một ảnh truy vấn**, có thể là cả khung cảnh hoặc ảnh crop một đối tượng. Đầu ra là danh sách **(video nguồn, đoạn [start, end], thời điểm đỉnh, điểm)**. Bài toán tương ứng với *Instance Search* (TRECVID INS) / *known-item search* (VBS) ở quy mô nhỏ.

Pipeline: lấy mẫu khung (đều theo fps, tuỳ chọn lọc trùng **aHash** theo ý tưởng DigUp) → đề xuất vùng (**lưới đa tỉ lệ** | OWLv2 | **SAM 3 / 3.1**) → embedding (**DINOv3 ViT-S/16**; DINOv2 / CLIP / SigLIP 2 để so sánh, qua cùng giao diện `Embedder`) → hai chỉ mục **FAISS IndexFlatIP** (`frame` và `region`) → truy vấn `frame` | `region` | `both` (= max theo (video, t)) → **gộp hit liền kề** thành đoạn thời gian → (tuỳ chọn) re-rank top-20 bằng vùng lưới hoặc SAM 3.

## Trạng thái (24/10/2026)
| Hạng mục | Trạng thái |
|---|---|
| Pipeline CPU (lấy mẫu, lưới, DINOv3/DINOv2/CLIP, FAISS, gộp đoạn) | Chạy được, đã đo trên DAVIS 2017 (10 và 70 video) |
| Demo Gradio `app.py` | Chạy thật trên CPU box (24/10/2026) |
| SAM 3 trên CPU | Chạy được trên box (bf16 autocast, bỏ `pin_memory`): khoảng 4 s/ảnh với ảnh mẫu, 8–14 s/frame DAVIS với 12 prompt; ảnh mẫu truck.jpg với prompt "truck" cho score 0.859 (26/10/2026) |
| SAM 3.1 / SAM 3 trên GPU | Đã có số: v2 và v3 cho 0 box/frame (nguyên nhân là prompt chung "object" + ngưỡng mặc định 0.5 của processor); v4 dùng prompt theo lớp. Xem results/RESULTS.md |
| OWLv2 region | Có mã, **chưa test** |
| EmbeddingGemma 2 | **Backbone mặc định** từ 27/10/2026: Kaggle T4 v7, 70 video hard R@1 0.948 / mAP@10 0.951 so với DINOv3 frame+grid 0.586 / 0.680 (xem bảng v7 bên dưới). Từ v8 (27/10/2026) chạy fp16 khi có GPU: độ chính xác giữ nguyên, query giảm từ 461 xuống 203 ms; late fusion, hai tầng và SAM 3 re-rank đều không thắng (xem mục v8) |

## Kết quả đo (box CPU 8 lõi dùng chung, 23/10/2026)
Số gốc: `results/RESULTS.md`, `results/*.json`, `results/eval_log.txt`, `results/eval_large_log.txt`.

**Benchmark tự dựng từ DAVIS 2017 val** (`scripts/prepare_davis.py`): 30 sequence ghép thành 10 video mp4 (24 fps, 854×480), lấy mẫu 1 fps = 73 khung. Region = lưới 2×2 + 3×3 (13 vùng/khung). 12 khung đầu mỗi sequence không đưa vào video; khung 0 dùng làm truy vấn, nên không rò rỉ. Một đoạn trả về là đúng nếu cùng video và chồng lấn đoạn GT (±0.5 s); mỗi GT chỉ khớp một lần.

Bộ truy vấn:
- `object`: 58 crop đối tượng (bbox mask +15%).
- `object_small`: 35 crop có mask < 5% khung.
- `object_hard`: 58 crop bị lật, thu 50%, tối 0.7 và dán lên nền nhiễu (`scripts/make_hard_queries.py`).
- `scene`: 30 khung đầy đủ.

### A. Truy vấn khó (`object_hard`, n = 58, 10 video)
| Encoder | Index | R@1 | R@5 | mAP@10 | Đỉnh top-1 ∈ GT |
|---|---|---|---|---|---|
| CLIP ViT-B/32 (baseline) | frame | 0.534 | 0.793 | 0.659 | 0.431 |
| CLIP ViT-B/32 | region | 0.293 | 0.707 | 0.475 | 0.241 |
| CLIP ViT-B/32 | both | 0.293 | 0.741 | 0.478 | 0.241 |
| DINOv2-small | frame | 0.759 | 0.983 | 0.848 | 0.759 |
| DINOv2-small | region | 0.759 | 0.983 | 0.807 | 0.724 |
| DINOv2-small | both | 0.759 | 0.983 | 0.813 | 0.724 |
| DINOv3 ViT-S/16 | frame | 0.724 | 0.983 | 0.814 | 0.707 |
| DINOv3 ViT-S/16 | region | 0.759 | 0.966 | 0.832 | 0.759 |
| **DINOv3 ViT-S/16** | **both** | **0.776** | 0.966 | **0.844** | **0.776** |

### B. Bộ lớn có distractor: 70 video (10 val + 60 video DAVIS 2017 train không chứa đối tượng truy vấn), 276 khung @1 fps
| Cấu hình | object_hard R@1 | object_hard mAP@10 | object R@1 | object mAP@10 |
|---|---|---|---|---|
| CLIP B/32 frame (baseline) | 0.190 | 0.298 | 0.862 | 0.876 |
| DINOv3-S/16 frame | 0.552 | 0.644 | 0.862 | 0.907 |
| DINOv3-S/16 region (grid) | 0.586 | 0.680 | 0.966 | 0.957 |
| **DINOv3-S/16 frame+region** | **0.586** | **0.680** | **0.966** | **0.957** |

Thời gian index (CPU dùng chung, load ≈ 26): CLIP frame 276 vector mất 1305 s; DINOv3 frame+grid 3864 vector mất 1237 s (≈ 0.22 khung/s). Truy vấn: CLIP 138–1593 ms, DINOv3 127–220 ms (embed + FAISS + gộp đoạn).

### C. Đối tượng nhỏ và bộ dễ (10 video), R@1 / mAP@10
| Encoder | Query | frame | region | both |
|---|---|---|---|---|
| CLIP B/32 | object_small (35) | 0.886 / 0.921 | 0.829 / 0.898 | 0.829 / 0.898 |
| DINOv2-small | object_small (35) | 0.943 / 0.971 | 0.971 / 0.986 | 0.971 / 0.986 |
| DINOv3 ViT-S/16 | object_small (35) | 0.971 / 0.986 | 1.000 / 1.000 | 1.000 / 1.000 |
| CLIP B/32 | object (58) | 0.931 / 0.932 | 0.897 / 0.919 | 0.897 / 0.919 |
| DINOv2-small | object (58) | 0.966 / 0.963 | 0.983 / 0.971 | 0.983 / 0.971 |
| DINOv3 ViT-S/16 | object (58) | 0.983 / 0.971 | 1.000 / 0.980 | 1.000 / 0.980 |
| CLIP B/32 | scene (30) | 0.967 / 0.983 | 1.000 / 1.000 | 1.000 / 1.000 |
| DINOv2-small | scene (30) | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| DINOv3 ViT-S/16 | scene (30) | 0.967 / 0.983 | 1.000 / 1.000 | 1.000 / 1.000 |

R@10 = 1.0 ở mọi cấu hình của bộ 10 video (chỉ có 10 video), nên không dùng để so sánh.

### D. Nhận xét
1. **DINOv3 + index region (`both`) tốt nhất trên bộ khó**: R@1 0.776 / mAP 0.844 so với CLIP frame 0.534 / 0.659. Khi thêm 60 video distractor, khoảng cách tăng lên: 0.586 so với 0.190.
2. Với CLIP, crop vùng lưới **làm giảm** kết quả (embedding toàn cục bị nhiễu bởi crop cắt ngang). Với DINO, region giúp ở đối tượng nhỏ và bộ khó, nên region dùng DINO.
3. Hạn chế: mỗi đối tượng chỉ có trong một sequence (truy vấn cùng cảnh, khác thời điểm), nên benchmark dễ hơn thực tế. Tốc độ CPU đo trên box quá tải nên chậm hơn thực tế nhiều; cần đo lại trên T4.

### E. Chạy thử app (24/10/2026, CPU)
Truy vấn ảnh thiên nga đen trên kho 10 video DAVIS (DINOv3-S, region lưới): top-1 là `davis_00.mp4`, đoạn 0.0–6.0 s, đỉnh 3.0 s, điểm 0.911; GT của đối tượng này trong video là 2.4–3.9 s. Các video khác chỉ đạt 0.33–0.36. Mỗi truy vấn ≈ 0.8 s.

## Phân tích DigUp (chi tiết: `digup_eval/digup_analysis.md`)
Đã chạy thật DigUp 0.7.0-beta.3 (MIT, https://github.com/ARahim3/DigUp, commit `d6f1f48`) trên CPU box với 2 video Wikimedia Commons (28 s, CC BY-SA 4.0).
- **Kiến trúc**: engine Swift; EmbeddingGemma 2 (~740M, 768-d, text/ảnh/audio chung một không gian) qua llama.cpp, Q8_0 GGUF (865 MB, repo HF công khai, không cần token). ffmpeg lấy **1 khung mỗi 3 s**, **lọc trùng aHash 8×8** (lệch ≤ 4 bit thì bỏ), mỗi khung giữ lại mang khoảng [start, end]. Lưu SQLite + FTS5, tìm brute-force, không có FAISS/ANN. Chấm điểm z-score với `zGate` = 2.0 cộng điểm từ khoá.
- **Số đo**: index ≈ 5 phút cho 9 vector (≈ 30 s/vector trên CPU); truy vấn văn bản nguội 29.6–33.3 s, dịch vụ ấm 8.8–12.3 s để embed câu truy vấn.
- **Phát hiện**: kết quả ban đầu đúng là nhờ **tên file**; đổi tên file thì `zGate` mặc định trả về rỗng trên kho nhỏ/đồng nhất. Với `--zgate -10`, "zebra" đạt cos 0.779 / 0.754 so với 0.562 / 0.528 cho truy vấn không liên quan.
- **Điểm yếu với Đề 12**: **không có truy vấn bằng ảnh**, chỉ embed toàn khung (70 vision token/khung), không có vùng vật thể, chậm trên CPU, không có ANN.
- **Quyết định**: **mượn ý tưởng, không dùng làm nền**. Repo này mượn lọc trùng aHash (`--dedup`) và đoạn thời gian theo khung. Muốn lấy mẫu 1 khung/3 s như DigUp thì đặt `--fps 0.333` (mặc định của repo là 1 fps).

## Công nghệ
| Thành phần | Model / phiên bản | Thư viện | License | Lý do | Link |
|---|---|---|---|---|---|
| Encoder chính (lõi) | DINOv3 ViT-S/16 LVD-1689M (CLS ⊕ mean patch bỏ 4 register token, 768-d, 224×224) | transformers 5.20.2 | **DINOv3 License** (gated) | Đặc trưng instance/dense SOTA, nhỏ, chạy CPU | https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m · https://github.com/facebookresearch/dinov3 |
| Region / re-rank (lõi GPU) | SAM 3 / SAM 3.1 (`sam3.1_multiplex.pt`), repo commit 7f473cf | `sam3` (Meta) + `scripts/sam3_cpu.patch` | **SAM License** (gated) | Phân đoạn theo khái niệm/exemplar, tracking | https://github.com/facebookresearch/sam3 · https://huggingface.co/facebook/sam3.1 |
| Encoder so sánh | DINOv2-small | transformers | Apache 2.0 | Stand-in không gated | https://huggingface.co/facebook/dinov2-small |
| Baseline | CLIP ViT-B/32 | transformers | MIT | Baseline chuẩn | https://huggingface.co/openai/clip-vit-base-patch32 |
| Encoder tuỳ chọn | SigLIP 2 base (`google/siglip2-base-patch16-224`) | transformers | Apache 2.0 | Có sẵn trong `Embedder`, chưa đo | https://arxiv.org/abs/2502.14786 |
| Region tuỳ chọn | OWLv2 (`google/owlv2-base-patch16-ensemble`, objectness top-8) | transformers | Apache 2.0 | Open-vocab, chạy T4; chưa test | https://arxiv.org/abs/2306.09683 |
| Region CPU | Lưới 2×2 + 3×3, overlap 25% | tự cài | – | Không cần GPU | |
| Chỉ mục | FAISS IndexFlatIP | faiss-cpu 1.15.1 | MIT | Chính xác, đủ nhanh ở quy mô này | https://github.com/facebookresearch/faiss |
| Tham khảo | DigUp + EmbeddingGemma 2 | llama.cpp | MIT / Apache 2.0 | Phân tích, mượn aHash + lấy mẫu | https://github.com/ARahim3/DigUp · https://huggingface.co/google/embeddinggemma-2 |
| Video / UI | OpenCV 5.0.0.93, Gradio 6.30.0 | | Apache 2.0 | Đọc video, demo | |
| Dữ liệu | DAVIS 2017 trainval 480p | | Annotation CC BY 4.0 | GT thời gian từ mask | https://davischallenge.org/davis2017/code.html |
| Runtime | Python 3.13.5 (mã tương thích 3.12 theo đề), torch 2.14.1+cpu | | | | |

Thay đổi công nghệ: bỏ `open_clip_torch` (xung đột torchvision), dùng CLIP qua Transformers; DINOv2-small chỉ là stand-in lúc DINOv3 bị 403, sau khi được cấp quyền DINOv3 thành encoder chính; SAM 3.1 chuyển sang GPU Kaggle vì OOM trên CPU. Khảo sát đầy đủ: `research.md`.

## Cài đặt
```bash
git clone https://github.com/meiiie/tgmt-de12-video-image-search && cd tgmt-de12-video-image-search
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # + torch bản CPU/GPU phù hợp
export HF_TOKEN=...                        # token HF của bạn, đã được cấp quyền DINOv3 (và SAM 3.1 nếu dùng); KHÔNG commit
# tuỳ chọn SAM 3/3.1:
git clone https://github.com/facebookresearch/sam3 && (cd sam3 && git checkout 7f473cf && git apply ../scripts/sam3_cpu.patch && pip install -e .)
```

## Chạy nhanh
```bash
# 1. Dữ liệu benchmark (DAVIS 2017 trainval 480p, ~833 MB)
wget https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip && unzip DAVIS-2017-trainval-480p.zip -d data
python scripts/prepare_davis.py && python scripts/make_hard_queries.py

# 2. Lập chỉ mục. Mặc định: EmbeddingGemma 2, chỉ frame (cần sentence-transformers 6.2.0, transformers 5.20.2, torchvision)
python scripts/build_index.py --videos data/davis_bench/videos --out data/idx_eg2
#    Tuỳ chọn nhanh hơn ~20x khi truy vấn: DINOv3 + lưới (thêm --dedup 4 để lọc trùng aHash, --fps 0.333 để lấy 1 khung/3 s)
python scripts/build_index.py --videos data/davis_bench/videos --out data/idx_dinov3-vits16 \
  --model facebook/dinov3-vits16-pretrain-lvd1689m --regions grid

# 3. Truy vấn một ảnh
python scripts/query.py --index data/idx_dinov3-vits16 --image q.jpg --mode both --k 5

# 4. Đánh giá (R@1/R@5/mAP@10); --rerank grid|sam3 để re-rank top-20
python scripts/evaluate.py --index data/idx_dinov3-vits16 --queries data/davis_bench/queries_object_hard.json

# 5. Demo Gradio
python app.py --index data/idx_eg2 --videos data/davis_bench/videos                    # mặc định EG2, http://localhost:7860
python app.py --index data/idx_dinov3-vits16 --videos data/davis_bench/videos           # DINOv3 (backbone theo index)
python app.py --index data/idx_dinov3-vits16 --videos data/davis_bench/videos --share   # Colab/Kaggle: link *.gradio.live
```
`--regions` nhận `none | grid | owlv2 | sam3`. Toàn bộ bảng kết quả: `scripts/run_all_evals.sh` (10 video) và `scripts/run_large.sh` (70 video, distractor thêm bằng `scripts/add_distractors.py`).

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

## Kaggle / Colab GPU
- Colab/Kaggle: `notebooks/de12_colab.ipynb`, đặt `HF_TOKEN` qua Secrets.
- Kernel Kaggle private `holilihu/tgmt-de12-video-image-search` (`kaggle/`, T4): không dùng secret; trọng số DINOv3 và SAM 3.1 (chia phần, kiểm sha256) đọc từ dataset private qua `/kaggle/input`. Thiếu trọng số thì ghi `results/STATUS.txt` và dừng. Đo GPU bằng `scripts/gpu_bench.py`. Đẩy kernel: `kaggle kernels push -p kaggle/ -t 7000`. Chi tiết: `kaggle/README.md`.
- Giới hạn Kaggle: tối đa 2 phiên GPU đồng thời mỗi tài khoản; CLI không gắn được secret.

## Ảnh chụp màn hình
![Giao diện](docs/screenshots/01_ui.png)
![Kết quả truy vấn](docs/screenshots/02_results.png)

## Cấu trúc repo
```
vsearch/core.py           lấy mẫu khung, aHash dedup, vùng, Embedder, build_index, Searcher, merge_segments
vsearch/sam3_regions.py   đề xuất vùng SAM 3 (text prompt)
vsearch/rerank.py         re-rank top-K bằng vùng lưới / SAM 3
vsearch/weights.py        dò layout trọng số offline (Kaggle)
scripts/                  prepare_davis, make_hard_queries, add_distractors, build_index, query, evaluate, gpu_bench, run_*.sh, sam3_cpu.patch
app.py                    demo Gradio
notebooks/de12_colab.ipynb, kaggle/   chạy GPU
results/                  số đo thật (RESULTS.md, *.json, log)
digup_eval/               đánh giá DigUp
research.md               khảo sát SOTA + lựa chọn công nghệ
```

## Dữ liệu & giấy phép
- **DAVIS 2017** (https://davischallenge.org/davis2017/code.html): annotation CC BY 4.0; nguồn video gốc liệt kê trong SOURCES.md của gói. Repo không chứa dữ liệu, video hay trọng số.
- Distractor 60 video DAVIS 2017 train: `results/licenses_distractors.md`.
- Video thử DigUp: Wikimedia Commons, CC BY-SA 4.0 (`digup_eval/digup_analysis.md`).
- SAM 3 / 3.1: **SAM License** của Meta, trọng số gated, không phân phối lại.

## Built with DINOv3
Dự án này dùng DINOv3 (`facebook/dinov3-vits16-pretrain-lvd1689m`) của Meta theo **DINOv3 License** (https://ai.meta.com/resources/models-and-libraries/dinov3-license/). Khi phân phối trọng số hoặc sản phẩm phái sinh phải kèm license và ghi "Built with DINOv3"; công bố kết quả phải ghi nhận việc dùng DINOv3. Repo không phân phối trọng số DINOv3.

## Trích dẫn
- O. Siméoni et al., "DINOv3", arXiv:2508.10104, 2025.
- N. Carion et al., "SAM 3: Segment Anything with Concepts", arXiv:2511.16719, 2025; SAM 3.1 release notes: https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md
- M. Oquab et al., "DINOv2", arXiv:2304.07193, 2023.
- A. Radford et al., "CLIP", arXiv:2103.00020, 2021.
- M. Tschannen et al., "SigLIP 2", arXiv:2502.14786, 2025.
- M. Minderer et al., "Scaling Open-Vocabulary Object Detection" (OWLv2), arXiv:2306.09683, 2023.
- M. Douze et al., "The Faiss library", arXiv:2401.08281, 2024.
- J. Pont-Tuset et al., "The 2017 DAVIS Challenge on Video Object Segmentation", arXiv:1704.00675, 2017.
- DigUp, https://github.com/ARahim3/DigUp (MIT).

## Kết quả GPU (Kaggle T4, fp16, v2 — 26/10/2026)
70 video, truy vấn hard: DINOv3 frame R@1 0.552 / mAP@10 0.642; +region grid 0.586 / 0.680 (~25 ms/truy vấn). SAM 3 (v5, 12 prompt lớp, ngưỡng 0.3): 4.36 box/frame (2.633 s/frame, 4.73 GB VRAM); re-rank top-20 đạt 0.603 / 0.684 nhưng chậm thêm ~911 ms/truy vấn (936.6 ms tổng), các biến thể fusion đều kém hơn nên chỉ để tùy chọn. Chi tiết: results/RESULTS.md, results/kaggle_v7_de12_results.json.

## Quyết định cuối (v3, 26/10/2026)
Pipeline chốt: **DINOv3 ViT-S/16 + region grid + FAISS** (Built with DINOv3). Trên T4 fp16 đạt: 70 video hard R@1 0.586 / mAP@10 0.680; 10 video hard 0.759 / 0.838; khoảng 25 ms/truy vấn.
SAM 3.1 (v2) và SAM 3 `sam3.pt` (v3, nạp missing=0, unexpected=22) đều trả về 0 box/frame với prompt "object" ở ngưỡng 0.3, nên region SAM và re-rank không cải thiện được kết quả. SAM tốn khoảng 1.04 s/frame và 3.8 GB VRAM. Phần này được ghi là ablation âm; chi tiết ở results/RESULTS.md.

## Hybrid DINOv3 + SAM 3 (Kaggle v5, 27/10/2026)
Đã sửa lỗi SAM trả 0 box (nguyên nhân: prompt chung "object" + ngưỡng mặc định 0.5 của processor). SAM 3 hiện trả 4.0 box/frame (2.63 s/frame, 4.73 GB VRAM trên T4).
Re-rank top-20 bằng SAM trên 70 video hard: R@1 **0.603** so với 0.586 (frame+grid), mAP@10 0.684 so với 0.680, nhưng thêm khoảng **+911 ms/truy vấn** (936.6 so với 25.9 ms). Bộ 10 video không cải thiện (0.759 so với 0.759). Bảng đầy đủ ở results/RESULTS.md; dữ liệu nguồn: results/kaggle_v5_de12_results.json.

## Vector store (FAISS / ChromaDB) có làm EG2 nhanh hơn không? (box CPU, 27/10/2026)

Script: `scripts/bench_vectorstore.py` → `results/vectorstore_bench.json`. CPU box, 1 luồng khi truy vấn, k=10, 100 truy vấn đo latency; recall@10 so với FlatIP (exact). Vector "real" = index EG2 10 video còn trên box (73 vector, 768-d; index 70 video 276 vector không còn trên box). 100k/1M là **vector tổng hợp có cụm (Gaussian mixture), không phải embedding thật** — recall của ANN trên dữ liệu thật có thể khác. ChromaDB 1.5.9 chỉ đo tới 100k (nạp 1M quá lâu cho box dùng chung). faiss-cpu 1.15.1.

| Tập | Store | Build (s) | RAM (MB) | p50 / p95 (ms) | recall@10 |
|---|---|---|---|---|---|
| real 73×768 | FAISS FlatIP (app hiện tại) | 0.00 | 1 | 0.008 / 0.009 | 1.000 |
| real 73×768 | FAISS HNSW32 | 0.00 | 1 | 0.013 / 0.015 | 1.000 |
| real 73×768 | ChromaDB (persistent) | 0.09 | 26 | 0.70 / 1.16 | 1.000 |
| 100k×768 | FlatIP | 0.23 | 293 | 18.5 / 20.9 | 1.000 |
| 100k×768 | HNSW32 ef64 | 2.6 | 319 | 0.11 / 0.21 | 0.988 |
| 100k×768 | IVF1264-Flat np16 | 6.7 | 373 | 0.36 / 0.44 | 1.000 |
| 100k×768 | IVF-PQ96x8 np16 | 16.8 | 21 | 0.17 / 0.20 | 0.512 |
| 100k×768 | ChromaDB | 18.0 | 482 | 1.53 / 1.95 | 1.000 |
| 100k×256 (MRL) | FlatIP / HNSW / Chroma | 0.05 / 1.4 / 10.1 | 98 / 122 / 197 | 3.18 / 0.06 / 0.81 | 1.0 / 0.987 / 1.0 |
| 1M×768 | FlatIP | 3.2 | 2918 | 237.6 / 292.9 | 1.000 |
| 1M×768 | HNSW32 ef64 | 46.3 | 3178 | 0.37 / 0.59 | 0.690 |
| 1M×768 | IVF4000-Flat np16 | 48.6 | ~3500 | 1.42 / 1.84 | 1.000 |
| 1M×768 | IVF-PQ96x8 np16 | 86.2 | nhỏ | 0.56 / 0.66 | 0.351 |
| 1M×256 (MRL) | FlatIP / HNSW / IVF-Flat | 0.8 / 19.1 / 15.0 | 977 / 1225 / 1037 | 81.0 / 0.20 / 0.47 | 1.0 / 0.877 / 1.0 |

**End-to-end** (encode EG2 + search): encode query ≈ 457 ms fp32 / ≈ 203 ms fp16 trên T4 (v7/v8). Với index của Đề 12 (73–276 vector) search < 0.02 ms = <0.01% thời gian → đổi sang HNSW/IVF/Chroma **không nhanh hơn** (Chroma còn chậm hơn FlatIP ~90 lần vì overhead client). Store chỉ có ý nghĩa khi index lớn: ở 100k vector FlatIP tốn 18.5 ms CPU (~9% của 203 ms), ở 1M tốn 238 ms (≈ bằng thời gian encode) → lúc đó IVF-Flat (1.4 ms, recall 1.0) hoặc HNSW (cần tăng efSearch để recall >0.69) mới đáng dùng. PQ nén RAM mạnh nhưng recall thấp trên dữ liệu này.

**Query cache** (sha256 của byte ảnh → embedding): lần lặp lại bỏ qua forward EG2. Hash + tra dict cho 150 KB: p50 0.087 ms; trong `Searcher.search` với ảnh 640×480 (hash pixel + search + merge) đo được 11.7 ms so với ~460 ms. Chỉ có lợi khi người dùng gửi lại đúng ảnh.

Đã thêm vào app (mặc định **tắt**, giữ FlatIP exact): `--hnsw-min N` (index ≥N vector chuyển sang FAISS HNSW32) và `--query-cache N` (LRU N embedding). Đã kiểm tra bằng embedder giả: HNSW cho kết quả giống FlatIP trên index 73 vector, lần gọi thứ 2 không gọi encoder.

Kết luận: nút thắt của EG2 là forward pass của model, không phải tìm kiếm. Muốn nhanh hơn thì dùng fp16/GPU (đã làm), model nhỏ hơn, hoặc cache; vector store chỉ cần khi kho vượt ~10^5 vector.

Nguồn: FAISS paper — Douze et al., "The Faiss library", arXiv:2401.08281; FAISS wiki "Guidelines to choose an index" (github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index); HNSW — Malkov & Yashunin, arXiv:1603.09320; Jégou et al., "Product Quantization for Nearest Neighbor Search", TPAMI 2011; ChromaDB docs (docs.trychroma.com) — việc Chroma dùng HNSW bên dưới dựa trên tham số `hnsw:space` trong docs, chi tiết nội bộ **chưa xác minh**.
