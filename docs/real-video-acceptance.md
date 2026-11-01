# Video dài: kiểm chứng trên nội dung thực tế

Ngày 01/11/2026, dùng video Goose Goose Duck do người dùng cung cấp trên máy. File gốc và các ảnh trích không được đưa vào Git hoặc gửi lên dịch vụ ngoài. Đây là kiểm chứng tích hợp trên một video; không phải benchmark độ chính xác đại diện cho mọi loại nội dung.

## Dữ liệu và cách chạy

- H.264 MP4, 1920 × 1080, 60 fps, 7.886,3 giây (2:11:26), 2.033.615.757 byte.
- EG2 revision `f9972ac22e696a105c482202646979e33e4b5a1e`, 768 chiều, 140 vision tokens.
- Quét toàn bộ ở 0,1 fps: 789 khung, mỗi 10 giây một khung. Chế độ này có thể bỏ qua cảnh ngắn nằm giữa hai mốc; muốn tìm chi tiết hơn cần tăng tần suất và lập lại chỉ mục.
- Máy kiểm thử: Intel i7-11800H (8 nhân/16 luồng), RAM 16 GB, RTX 3050 Ti Laptop 4 GB, driver 566.07. Bản CPU dùng FP32; phép thử CUDA riêng dùng BF16, không dùng FP16.

`scripts/probe_real_video.py` trích 16 mốc trải đều và đo cách đọc video. Trên 12 mốc từ 0 đến 110 giây, đọc tuần tự mất 3,617 giây, seek mất 1,289 giây; cả hai trả cùng timestamp. Đây chỉ là thời gian đọc khung, không bao gồm inference, và chưa phải phép đo lặp kiểm soát cache.

`scripts/verify_real_video.py --session <session.json> --cases <cases.json> --output <folder> --wait 3600` chờ chỉ mục hoàn tất, chạy truy vấn, lưu top 5 thumbnail để đối chiếu, đo thời gian HTTP, kiểm tra giới hạn thời gian, byte-range ở cuối file và kích thước/mtime nguồn. Session chứa token nội bộ, luôn nằm trong thư mục bị Git bỏ qua.

## Những sửa đổi phát sinh từ phép thử

- Seek tại mốc lấy mẫu khi khoảng cách ít nhất hai giây; lưu timestamp mà decoder thực sự trả về.
- Hiển thị thời lượng trước khi model tải xong, tốc độ xử lý, ETA và mốc đã xử lý. Kết quả khi đang lập chỉ mục có thông báo giới hạn dữ liệu.
- Truy vấn ảnh giữ điểm từng khung. Truy vấn chữ làm mượt theo khoảng ba giây, thay vì luôn gộp ba khung dù chúng cách nhau mười giây. Kiểm thử chứng minh khung khớp chính xác không bị cảnh giống tương đối kéo xuống hạng dưới.
- Chọn một video và giới hạn từ/đến phút. Lọc trước khi chấm điểm; đầu/cuối kết quả được giới hạn trong phạm vi đó.
- Cache truy vấn dùng khóa riêng, để truy vấn đã có embedding không phải đợi lô inference đang chạy.

## Bằng chứng đã xác nhận

- Tạm dừng và khởi động lại worker tại 160 khung giữ nguyên checkpoint 1.600 giây; tiếp tục không lập lại từ đầu.
- Truy vấn tiếng Việt “màn hình bỏ phiếu có nhiều dấu X đỏ” trả về những màn hình phù hợp trong phần đã xử lý, đã đối chiếu bằng giao diện.
- Trình phát đến 1.700 giây, `readyState=4`, chiều rộng 1920, vẫn dừng và không phát âm thanh.
- Lưu khoảnh khắc 28:20–28:25 và xuất MP4 qua hộp thoại trong tab Codex. File xuất giải mã đủ 300 khung, đúng 5,0 giây, 1080p/60 fps. Sai khác pixel trung bình của khung đầu so với nguồn tại 1.700 giây là 0,81/255 sau encode.
- 19 kiểm thử backend qua trên Python đóng gói 3.14.10. Bốn luồng UI hiện có và luồng lọc thời gian mới đều qua; luồng mới đã chạy lại sau khi sửa locator của kiểm thử.

Bằng chứng chi tiết nằm trong `outputs/real-video/`: `probe.json`, `restart.json`, `runtime-tests.log`, `ui-tests.log`, `ui-time-range.log`, `export-verification.json`, `desktop-real-video.jpg`, clip `vote-28m20s.mp4`. Các tệp này không thuộc repository công khai.

## Kết quả trên toàn video

Lượt CPU lưu 396 khung trước khi chuyển worker sang CUDA; giữ nguyên checkpoint rồi hoàn tất 393 khung còn lại. Log theo dõi CUDA từ giai đoạn tải model đến hoàn tất ghi nhận 168,7 giây; các lô ổn định đạt khoảng 2,9–3,1 khung/giây khi tính cả đọc video, embedding, thumbnail và SQLite. Đây không phải thời gian quét toàn bộ video từ đầu bằng GPU.

Toàn bộ 789 vector có 768 chiều, timestamp duy nhất từ 0 đến 7.880 giây, khoảng cách 10 giây. SQLite `quick_check` trả `ok`; sai lệch norm lớn nhất 1,2e-7. Fingerprint nguồn không đổi. Thư viện gồm chỉ mục, thumbnail và dữ liệu phụ chiếm khoảng 18,3 MiB, không tính model nằm ở thư mục riêng và file nguồn 2,03 GB.

Mười truy vấn HTTP khi model CUDA đã nóng mất 14–480 ms. Các con số riêng lẻ không phải percentile và không gồm thời gian khởi động/tải model. Bảng dưới là đối chiếu bằng mắt trên tập tình huống nhỏ này:

| Trường hợp | Kết quả đầu | Nhận xét |
|---|---|---|
| Chữ EN: voting screen with red crosses | 1:28:40 | Đúng màn hình bỏ phiếu |
| Chữ VI: màn hình bỏ phiếu có nhiều dấu X đỏ | 1:51:10 | Sai: màn hình vai trò; kết quả thứ hai 1:28:40 đúng |
| Chữ EN: waiting room with colorful geese | 1:07:40 | Đúng phòng chờ nhiều nhân vật |
| Chữ EN: black end screen with subscribe | 2:11:20 | Đúng màn hình kết |
| Chữ VI: màn hình giới thiệu logo kênh màu đỏ | 28:10 | Sai: thông báo tìm thấy xác màu đỏ |
| Chữ EN: bỏ phiếu, giới hạn phút 50–70 | 1:01:20 | Đúng cảnh và trong khoảng yêu cầu |
| Ảnh intro tại 0:00 | 0:00 | Đúng mốc |
| Ảnh họp tại 8:45,68 | 8:50 | Lệch 4,32 giây, đúng cảnh |
| Ảnh phòng chờ tại 52:34,12 | 52:30 | Lệch 4,12 giây, đúng cảnh |
| Ảnh kết tại 2:11:25,30 | 2:11:20 | Lệch 5,30 giây, đúng cảnh |

Bốn truy vấn ảnh đều trả mốc gần ảnh tham chiếu trong lưới lấy mẫu. Hai thất bại tiếng Việt được giữ trong báo cáo; không đổi truy vấn hay gắn nhãn lại để che chúng. Kết quả tốt trên phần đầu chưa bảo đảm thứ hạng tốt khi tìm toàn video. Chất lượng truy vấn tiếng Việt và dữ liệu đánh giá rộng hơn là công việc tiếp theo trước khi tuyên bố chất lượng sử dụng phổ quát.

Chi tiết: `acceptance/report.json`, `acceptance/manual-review.json`, `acceptance/top-results.jpg`, `acceptance/index-progress.json`, `integrity.json`. Byte-range 100 byte cuối file trả HTTP 206.

## Bản đóng gói và thời gian khởi động

Release executable biên dịch thành công. Engine CPU và engine CUDA lấy từ thư mục phát hành đều qua kiểm tra source khớp repository, truy vấn EG2 chữ/ảnh, HTTP 401 khi thiếu token, HTTP 206 cho media và xuất/giải mã clip 2,002 giây. Bằng chứng: `packaged-cpu-final.json`, `packaged-cuda.json`.

Tab Codex cuối cùng dùng trực tiếp `outputs/releases/FrameAtlas-CUDA/runtime/python.exe` và engine đi kèm, không phụ thuộc thư mục thử nghiệm CUDA. Khởi động lại giữ nguyên một video sẵn sàng, 789 khung và một khoảnh khắc đã lưu. Truy vấn đầu sau khởi động mất 23.426 ms gồm tải model; trả đúng mốc 5.320 giây. Vì vậy không áp dụng các số đo 14–480 ms khi model đã nóng cho lần mở ứng dụng đầu tiên. Bằng chứng: `live-packaged-cuda.json`.

Ứng dụng native được build nhưng không mở cửa sổ trong lượt này để không ảnh hưởng việc học của người dùng. Giao diện được kiểm tra trong tab bên phải Codex. Bộ nén NSIS đã dừng; sản phẩm giao ở dạng portable.

ZIP CPU hiện tại có 15.080 file, 433.160.962 byte; CRC và đối chiếu source/executable trong ZIP đều qua. SHA-256: `717782979729c2e896eb91e11c34332c3b76438e2d9f64dea7a960652a8b1d06`. Manifest riêng cho từng biến thể nằm cạnh ZIP dưới `outputs/releases/`.

ZIP CUDA có 15.116 file, 3.449.353.376 byte (khoảng 3,21 GiB); CRC và đối chiếu engine/executable/manifest bên trong ZIP đều qua. SHA-256: `47ac62acd0c5b405be99919090eda4bff39550ba097572a5429cfb3189ea56dd`. Gói lớn hơn do thư viện CUDA đi kèm. Thư mục `outputs/releases/FrameAtlas-CUDA/` đã sẵn sàng dùng mà không cần giải nén lại. Chưa mở native window trong lượt này; worker của chính thư mục đó đã được kiểm tra.

Giao diện cuối cùng lọc phút 50–70, trả cảnh bỏ phiếu tại 1:01:20 và trình phát xác nhận `currentTime=3680`, `readyState=4`, `paused=true`, `videoWidth=1920`. Ảnh bằng chứng: `outputs/real-video/desktop-final.jpg`.

## Giới hạn cần giữ rõ

EG2 trong sản phẩm này đang tìm theo hình ảnh. Cảnh họp, phòng chờ và cảnh chơi có thể nhận ra bằng mô tả hoặc ảnh; câu hỏi về lời nói, suy luận vai trò hay diễn biến chỉ thể hiện qua âm thanh cần lớp transcript riêng. Điểm tương đồng không phải xác suất đúng. Những vòng chơi có bố cục lặp lại có thể trả nhiều khoảnh khắc tương tự; nên dùng ảnh tham chiếu và phạm vi thời gian.

## Nguồn cho thử nghiệm GPU

Phép đo CUDA dùng đúng 12 khung đầu đã có vector CPU, đọc lại từ file nguồn tại cùng timestamp. Ba lô gồm 4 khung/lô mất lần lượt 5,682 / 0,605 / 0,577 giây; hai lô sau đạt 6,768 khung/giây cho riêng embedding, chưa tính decode, thumbnail và SQLite. Peak memory allocated 999,9 MiB, reserved 1.076 MiB. Đây là mẫu nhỏ trên máy đang chạy các tác vụ khác, không phải mức bảo đảm cho mọi video.

Cosine giữa CPU FP32 và CUDA BF16 nằm trong khoảng 0,998794–0,999927. Vector BF16 được chuyển sang FP32 rồi chuẩn hóa lại trước khi lưu/chấm điểm; nếu chỉ chuyển kiểu sau bước chuẩn hóa BF16, norm có thể lệch và dot product vượt 1. Kiểm thử riêng bảo vệ hành vi này.

- [PyTorch: cài đặt theo nền tảng tính toán](https://pytorch.org/get-started/locally/).
- [NVIDIA: tương thích phiên bản CUDA và driver](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).
- Gói thử nghiệm lấy trực tiếp từ index chính thức `https://download.pytorch.org/whl/cu126`. Kết quả hiệu năng và độ tương đồng CPU/GPU được ghi bằng `scripts/benchmark_desktop_cuda.py`; không suy diễn tốc độ từ thông số GPU.
