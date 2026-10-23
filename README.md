# Đề 12 – Tìm kiếm ảnh / đối tượng trong video → video nguồn + thời điểm

Pipeline: lấy mẫu khung (uniform fps, tuỳ chọn lọc trùng aHash kiểu DigUp) → vùng (lưới đa tỉ lệ | OWLv2 | SAM 3) → embedding (DINOv3 / DINOv2 / CLIP / SigLIP 2, giao diện `Embedder` thay được) → FAISS IndexFlatIP riêng cho `frame` và `region` → truy vấn ảnh (frame | region | both) → gộp hit liền kề thành đoạn [start, end] + thời điểm đỉnh.

```
vsearch/core.py          frames, regions, Embedder, build_index, Searcher, merge_segments
vsearch/sam3_regions.py  SAM 3 region proposals (text prompt)
scripts/prepare_davis.py tạo benchmark từ DAVIS 2017 val (GT thời gian từ mask)
scripts/make_hard_queries.py  truy vấn khó (lật, thu nhỏ, tối, nền nhiễu)
scripts/build_index.py | query.py | evaluate.py | run_all_evals.sh
app.py                   demo Gradio
notebooks/de12_colab.ipynb  chạy trên Colab/Kaggle GPU
research.md              khảo sát + lựa chọn công nghệ ; results/RESULTS.md  số đo thật
```

Chạy nhanh (CPU):
```bash
pip install -r requirements.txt            # DINOv3 cần HF_TOKEN đã được cấp quyền: source ../.env
wget https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip && unzip -d data ...
python scripts/prepare_davis.py && python scripts/make_hard_queries.py
python scripts/build_index.py --videos data/davis_bench/videos --out data/idx_dinov3-vits16 --model facebook/dinov3-vits16-pretrain-lvd1689m --regions grid
python scripts/evaluate.py --index data/idx_dinov3-vits16 --queries data/davis_bench/queries_object_hard.json
python scripts/query.py --index data/idx_dinov3-vits16 --image q.jpg --mode both
python app.py --index data/idx_dinov3-vits16 --videos data/davis_bench/videos
```
Lưu ý box: torchvision của torch 2.14 hệ thống bị lệch → venv cài `torchvision==0.29.1+cpu --no-deps`. SAM 3 repo hard-code `device="cuda"` ở 4 file; bản clone `/workspace/tgmt/sam3` đã vá để chạy CPU (chậm).


## Built with DINOv3
Dự án này dùng DINOv3 (`facebook/dinov3-vits16-pretrain-lvd1689m`) của Meta, phát hành theo **DINOv3 License** (https://ai.meta.com/resources/models-and-libraries/dinov3-license/), không phải giấy phép mã nguồn mở thông thường: được dùng/sửa/phân phối (kể cả thương mại) nhưng khi phân phối trọng số hoặc sản phẩm phái sinh phải kèm bản license và ghi rõ "Built with DINOv3"; công bố kết quả phải ghi nhận việc dùng DINOv3; tuân thủ điều khoản kiểm soát thương mại. Repo này không phân phối trọng số DINOv3 (tải từ Hugging Face sau khi được Meta cấp quyền). Paper: https://arxiv.org/abs/2508.10104
