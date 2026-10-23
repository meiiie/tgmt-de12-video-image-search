# Đánh giá DigUp cho Đề 12 (tìm hình ảnh/vật thể trong video)

Ngày đo: 23/10/2026, giờ Việt Nam (UTC+7). Máy: box CPU "Intel Xeon Processor", 8 lõi, 15 GB RAM, không có GPU.
Repo: https://github.com/ARahim3/DigUp, commit `d6f1f480427d151640196e4d6588906e1f3ee782` (22/10/2026), license MIT.
Binary dùng: bản Linux `DigUp_0.7.0-beta.3_amd64.deb` (release ngày 22/10/2026, 17:45 UTC+7). Mình giải nén bằng `dpkg-deb -x`, không cài, rồi chạy CLI `usr/lib/DigUp/helper/digup`. Không build từ mã nguồn vì box không có Swift 6.4.

## 1. Kết quả chạy thử (số đo thật)
- **Chạy được trên CPU.** Không cần token HF hay API trả phí: `digup download-model` tải 2 file GGUF (865 MB) từ repo HF công khai `ggml-org/embeddinggemma-2-GGUF` trong khoảng 11 s.
- Mẫu thử: 2 video từ Wikimedia Commons, tổng 28 s, license CC BY-SA 4.0 (chi tiết ở mục 6).
- **Thời gian lập chỉ mục** (`digup index`, theo log của tool):
  - Zebra_Nairobi.webm (8 s): 2 frame, 0 cửa sổ âm thanh, mất 57,78 s. Con số này đã gồm cả thời gian nạp model.
  - Tame_Zebra.webm (19 s): 6 frame, 1 cửa sổ âm thanh, mất 240,87 s.
  - Tổng: khoảng 5 phút (lệnh chạy 299,5 s, gồm cả bước estimate) cho 9 vector: 8 frame, 1 audio và 2 segment tên file chỉ dùng cho FTS.
  - Kích thước index: 78 KB.
  - Công cụ `estimate` đoán "≈ 1 s", vì nó hiệu chỉnh theo M4 Pro. Trên CPU này, ước lượng đó sai hơn 2 bậc độ lớn.
- **Độ trễ truy vấn văn bản**:
  - CLI chạy nguội (khởi động tiến trình và nạp model): 29,6 / 31,3 / 33,3 s cho mỗi truy vấn.
  - Dịch vụ ấm (`search-service`): encoder sẵn sàng sau 19,4–24,5 s. Sau đó, embed câu truy vấn mất 8,8–12,3 s và tìm kiếm vector + FTS mất 0–19 ms. Truy vấn lặp lại trúng cache nên chỉ mất 0–3 ms.
- **Kết quả**:
  - Lúc đầu, truy vấn "zebra" trả về đúng 2 video, nhưng đó là nhờ **tên file** chứa chữ "zebra" (`segment: name`, khớp từ khóa FTS5).
  - Sau khi đổi tên file thành clip_a/clip_b, `search-service` với `zgate` mặc định 2.0 trả về **rỗng** cho mọi truy vấn. Lý do: index chỉ có 9 vector và toàn ngựa vằn, nên không frame nào "nổi bật" so với phân phối.
  - Với `--zgate -10`, kết quả trả về theo frame và có timestamp:
    - "zebra": clip_a frame tại 6,5 s (cos 0,779), clip_b frame tại 6,5 s (cos 0,754).
    - "a red car on a highway": cos chỉ 0,562 và 0,528.
  - Nghĩa là model vẫn phân biệt được qua cosine. Riêng ngưỡng z-gate lại không phù hợp với kho nhỏ hoặc kho đồng nhất.
- Log: `index.log`, `warm.log`, `warm2.log`, script `warm.py` (cùng thư mục).

## 2. Kiến trúc (đọc từ mã nguồn)
- **Ngôn ngữ**: engine Swift (`Sources/DigUpKit`). Bản Mac dùng SwiftUI; bản Windows/Linux dùng Tauri làm vỏ, gọi CLI `digup` qua JSON lines (`search-service`, `index-service`).
- **Model**: EmbeddingGemma 2, khoảng 740M tham số, embedding 768 chiều, chung một không gian cho text, ảnh, audio và video. Model chạy qua llama.cpp tag `b11461` (commit `4d756bc7`, có một patch "no-logits"), bản lượng tử Q8_0:
  - `embeddinggemma-2-Q8_0.gguf`, 310 MB, phần text.
  - `mmproj-embeddinggemma-2-Q8_0.gguf`, 555 MB, phần vision/audio.
  - Revision được ghim là `bfcd2987…` (`Sources/DigUpKit/ModelFiles.swift`).
- **Embed video** (`Platform/Portable/Media+Portable.swift`, `VideoExtractor.keyframes`; tham số trong `Model.swift`):
  - ffmpeg lấy 1 frame mỗi `frameInterval = 3.0` s, bắt đầu từ 0,5 s, tối đa 1200 frame mỗi video, rồi scale cạnh dài về 1024 px.
  - **Lọc trùng theo shot**: tính average-hash 8×8. Frame nào lệch ≤ 4 bit so với frame được giữ gần nhất thì bị bỏ. Mỗi frame được giữ đại diện cho khoảng [start, start của frame giữ kế tiếp].
  - Mỗi frame được embed như một ảnh, với ngân sách `frameBudget = 70` vision token. Con số này thấp; ảnh thường được 140, screenshot 280.
  - Âm thanh: cửa sổ 30 s, bước nhảy 25 s, bỏ qua đoạn im lặng.
  - **Không có** embedding thời gian (temporal) ở mức clip: video chỉ là tập các ảnh tĩnh.
- **Lưu trữ/index** (`IndexStore.swift`, `Database.swift`):
  - Một file SQLite gồm các bảng `files`, `segments` (kind=frame, modality=image, loc=start, end, vector BLOB float16) và `fts` (FTS5 porter/unicode61 trên tên file, thư mục, OCR, text).
  - **Không dùng FAISS hay ANN**: khi tìm, toàn bộ vector được nạp vào RAM rồi tính brute-force matrix-vector theo khối (`Searcher.score`).
- **Truy vấn** (`Searcher.swift`): là truy vấn lai.
  - (a) Tính cosine với mọi vector, trừ trung bình theo modality, chia độ lệch chuẩn để ra z-score. Chỉ những segment có z ≥ `zGate` (2.0) mới được tính là khớp nghĩa.
  - (b) FTS5 bm25 trên chữ.
  - (c) Điểm cuối = z + thưởng theo độ phủ từ (`word-weight` 2.0) + 1 nếu câu hỏi nhắc tới loại file ("in a video").
  - Kết quả gộp theo file và trỏ tới mốc giây của segment tốt nhất. Có lớp "weaker matches fold".
  - **Chỉ có truy vấn bằng văn bản**: CLI là `search <words>`, giao thức `search-service` chỉ nhận `q` dạng text. `embedImages` có tồn tại nhưng chỉ phục vụ việc lập chỉ mục. Không có truy vấn bằng ảnh hay vùng vật thể.
- **Đánh giá**: lệnh `digup eval` tính recall trên các file JSON trong `evals/` (synthetic, multilingual, code). Đây là bộ tự tạo, không phải benchmark video.

## 3. Điểm mạnh
- Chạy hoàn toàn cục bộ, model mở (Apache 2.0), không cần token. Pipeline ffmpeg lấy mẫu → lọc trùng → embed → SQLite gọn và tái lập được (revision và tag được ghim, có test vector tham chiếu).
- Một không gian chung cho text, ảnh và audio, đa ngôn ngữ. Có mốc thời gian theo frame và theo cửa sổ âm thanh.
- Lọc shot bằng aHash rẻ mà hiệu quả. Truy vấn lai embedding + từ khóa thực dụng. Có công cụ đo chi phí (`speed`, `costs.json`).

## 4. Điểm yếu (đối với Đề 12)
- **Không truy vấn bằng ảnh/vật thể**, trong khi đây là yêu cầu cốt lõi của đề.
- **Chỉ embed toàn khung hình**, không có vùng vật thể (không detector/segmenter). Ngân sách 70 token cho mỗi frame nên khó tìm vật thể nhỏ.
- **Chậm trên CPU**: khoảng 30 s cho mỗi vector khi lập chỉ mục, khoảng 10 s để embed một câu truy vấn trên box này. Muốn chạy trên Colab/Kaggle GPU thì phải tự build llama.cpp với CUDA.
- Không có ANN (FAISS/HNSW), nên với hàng triệu frame vừa tốn RAM vừa chậm. Không có re-ranking hình học hay cục bộ.
- Z-gate làm hỏng kho nhỏ hoặc đồng nhất (đã đo ở trên: trả về rỗng). Tên file tác động mạnh tới kết quả, nên nếu đánh giá mà không đổi tên file thì số liệu bị "rò" nhãn.
- Engine viết bằng Swift, khó tích hợp vào notebook Python. Gộp kết quả theo file chứ không trả nhiều đoạn thời gian trong cùng một video.

## 5. Khuyến nghị: mượn ý tưởng, KHÔNG dùng làm nền
**Nên mượn**:
- Lấy mẫu cố định 1 frame/2–3 s kèm lọc trùng bằng aHash hoặc pHash theo shot, mỗi frame mang khoảng [start, end].
- Lưu metadata và vector vào SQLite, ghim phiên bản model vào index.
- Chấm điểm z-score theo phân phối (bật hoặc tắt được), truy vấn lai với từ khóa.
- Có thể dùng EmbeddingGemma 2 làm baseline toàn khung hình cho truy vấn text→video.

**Hướng đề xuất cho đồ án** (Python, chạy được trên Colab/Kaggle):
- Lấy mẫu bằng ffmpeg/PySceneDetect.
- **SAM 3 / SAM 3.1** sinh mask vật thể (theo prompt khái niệm, có tracking qua video) → crop vùng.
- **DINOv3** embed toàn khung + từng vùng, đây là đặc trưng thị giác thuần, mạnh cho instance retrieval ảnh→ảnh. Có thể thêm SigLIP 2 hoặc EmbeddingGemma 2 cho truy vấn text.
- **FAISS** (IVF/HNSW) cho cả 2 chỉ mục, re-rank (ví dụ so khớp patch hoặc local feature), gộp các hit gần nhau thành đoạn thời gian.

**Lưu ý**: SAM 3, SAM 3.1 và DINOv3 trên HF đều **gated** (`gated: manual`, license "other"), nên cần token HF và phải chấp nhận license. DigUp thì không cần.

**Kiểm chứng sự tồn tại** (đã gọi HF API và GitHub, 23/10/2026):
- SAM 3.1: **có**, https://huggingface.co/facebook/sam3.1 (tạo 26/03/2026, gated)
- SAM 3: https://huggingface.co/facebook/sam3 (tạo 07/11/2025, gated), mã nguồn https://github.com/facebookresearch/sam3
- DINOv3: **có**, https://github.com/facebookresearch/dinov3, ví dụ checkpoint https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m (gated)
- EmbeddingGemma 2: **có**, https://huggingface.co/google/embeddinggemma-2 (Apache 2.0, không gated, tạo 14/09/2026)

## 6. Danh sách công nghệ
| Thành phần | Phiên bản/checkpoint | Lý do | Nguồn |
|---|---|---|---|
| DigUp | commit d6f1f48; binary v0.7.0-beta.3 | Đối tượng đánh giá | https://github.com/ARahim3/DigUp |
| EmbeddingGemma 2 (Q8_0 GGUF) | ggml-org/embeddinggemma-2-GGUF @ bfcd298762cc34d0357ece5ebdd31791a3a374d8 | Model embedding đa phương thức mà DigUp dùng | https://huggingface.co/ggml-org/embeddinggemma-2-GGUF |
| llama.cpp | b11461 (4d756bc7) | Runtime suy luận trên CPU/Vulkan/Metal | https://github.com/ggml-org/llama.cpp |
| ffmpeg/ffprobe | bản đóng gói kèm .deb | Lấy mẫu frame, đọc audio | https://ffmpeg.org |
| SQLite + FTS5 | bản vendor | Lưu vector + từ khóa | https://sqlite.org/fts5.html |
| SAM 3.1 (đề xuất) | facebook/sam3.1 | Mask vật thể/khái niệm, tracking video | https://huggingface.co/facebook/sam3.1 |
| DINOv3 (đề xuất) | ví dụ dinov3-vits16-pretrain-lvd1689m | Đặc trưng instance ảnh→ảnh | https://github.com/facebookresearch/dinov3 |
| FAISS (đề xuất) | chưa cài | ANN cho chỉ mục lớn | https://github.com/facebookresearch/faiss |
| Mẫu 1 | "Tame Zebra.webm", 19,7 s, CC BY-SA 4.0, tác giả Bernard303 | Video thử | https://commons.wikimedia.org/wiki/File:Tame_Zebra.webm |
| Mẫu 2 | "Zebra at Nairobi National Park.webm", 8,45 s, CC BY-SA 4.0, tác giả ROCKY | Video thử | https://commons.wikimedia.org/wiki/File:Zebra_at_Nairobi_National_Park.webm |

(Trong thư mục `sample/`, 2 mẫu đã được đổi tên thành `clip_a.webm` (Tame Zebra) và `clip_b.webm` (Nairobi) để bỏ tác động của tên file.)
