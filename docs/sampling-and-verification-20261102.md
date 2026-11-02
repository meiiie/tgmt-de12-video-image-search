# Lấy mẫu và đối chiếu ảnh trên video thực tế

Phạm vi: giảm bỏ sót do lấy mẫu thưa, giảm kết quả chỉ giống về ngữ nghĩa khi người dùng muốn tìm lại ảnh gốc; giữ tìm bằng ngôn ngữ tự nhiên. Mọi thao tác do agent chính thực hiện. Video và ảnh riêng tư ở máy người dùng, không nằm trong Git hoặc gói phát hành.

## Cách dùng và phạm vi cam kết

Trong **Cài đặt → Cách lấy khung hình**, chọn lấy mẫu đều hoặc **Mốc đều + bổ sung khi chuyển cảnh**. Chế độ mới giữ toàn bộ mốc đều, quét chuyển cảnh ở độ rộng 160 pixel và bổ sung một khung cách đầu cảnh tối đa 0,2 giây nếu nửa giây đầu chưa có mốc đều. Có thể tạm dừng, tiếp tục và hủy. Cache cut hoàn tất được ghi nguyên tử; chỉ mục có chữ ký `hybrid-v1` để không dùng lẫn với chỉ mục cũ. Đổi cách lấy mẫu cần lập chỉ mục lại.

Đây là cách giữ cảnh ngắn nằm giữa hai mốc lấy mẫu. Nó chưa bảo đảm giữ một vật thể chỉ thoáng xuất hiện trong một cảnh không đổi. Ngưỡng cut 10 chưa được hiệu chỉnh riêng cho gameplay; chớp sáng/đổi giao diện có thể tạo cut, còn chuyển cảnh mờ có thể bị bỏ qua. Video thực tế trong lượt này là CFR 60 fps; chưa có kiểm chứng riêng cho mọi dạng VFR.

Trong **Cách tìm ảnh**:

- **Nội dung tương tự** giữ cách tìm ngữ nghĩa bằng EG2, là mặc định. Có thể trả cảnh giống nhau dù không phải cùng ảnh/vật thể.
- **Đối chiếu chi tiết ảnh** lấy tối đa 48 khung có cosine cao nhất, kiểm tra SIFT, ratio/mutual matching, RANSAC homography, độ phủ và màu ảnh sau căn chỉnh. Không thay EG2 hoặc tiền xử lý embedding. Chế độ này phù hợp screenshot/crop có nhiều chi tiết; có thể từ chối đúng đối tượng khi đổi góc, chuyển động, che khuất hoặc thiếu texture.

Không dùng ngưỡng cosine trên DAVIS để tuyên bố xác suất đúng của video người dùng. Kết quả đối chiếu xếp theo bằng chứng chi tiết rồi cosine; khoảng hiển thị là ±1 giây quanh khung đã kiểm tra, cắt tại nguồn/phạm vi/cut. **Khoảng xem này không phải nhãn toàn bộ lần xuất hiện.** Không có kết quả chỉ có nghĩa chưa đủ bằng chứng trong tập ứng viên đã kiểm tra.

Tìm văn bản của chỉ mục đều giữ luồng cũ. Với chỉ mục hybrid, làm mượt theo trọng số thời gian thực trong ±1,5 giây, gộp đoạn trong từng shot; không coi các khung bổ sung là cách đều nhau. Vì bộ gộp đoạn cũng thay đổi, chênh lệch top-k giữa uniform và hybrid không thể quy hết cho riêng mật độ lấy mẫu. Độ phủ frame trên ground truth là phép đo riêng cho khâu lấy mẫu.

## Thiết kế phép đo

**DAVIS regression.** Dùng lại pilot có nhãn đã xem ở [lượt trước](image-retrieval-quality-20261101.md); không gọi đây là test mù mới. Chạy toàn bộ 201 query toàn cảnh hoặc object padding 40% với hai chế độ ảnh và ba cấu hình: đều 0,1 fps, hybrid 0,1 fps, đều 1 fps. Nhóm object test có 42 truy vấn dương từ 14 đối tượng/8 nguồn và 18 truy vấn vắng từ 6 đối tượng/6 nguồn. Các query của cùng đối tượng có tương quan. Cấu trúc clip dựng khiến cảnh test bị lệch pha với lưới 10 giây; độ phủ thấp của cấu hình đó không đại diện tất cả video.

**Video người dùng.** Dùng SQLite backup chỉ đọc để tạo thư viện mới, giữ thư viện cũ và khoảnh khắc đã lưu. [Protocol](lab/real-video-sampling-protocol.json) ấn định trước 9 mốc trên toàn video, mỗi mốc có toàn ảnh và crop vùng chơi game. Ảnh truy vấn trùng đúng khung index bị loại khỏi thống kê giữ ngoài. Đo tìm lại mốc nguồn trong ±3 giây ở top 1/top 5; không đo mọi lần xuất hiện của nhân vật. Baseline đều 0,1/0,5 fps lấy các anchor từ cùng ma trận embedding mới, tránh trộn model/preprocessing; baseline 0,1 fps không phải phép chạy lại thư viện lịch sử.

Sáu ảnh DAVIS ngoài nguồn là phép thử từ chối. Video 2 giờ chưa được gán nhãn vắng đầy đủ, nên không gọi tỷ lệ trả kết quả của chúng là false-positive rate của video thật. Cảnh game và HUD lặp lại khiến mốc khác vẫn có thể giống ảnh. Xem trực tiếp các kết quả, không tự gán mọi mốc ngoài ±3 giây là nhận nhầm danh tính.

Không chỉnh tham số verifier theo kết quả test. Báo cáo giữ cả ca bỏ sót, không chỉ ảnh trúng. Model là EG2 revision cố định trong source, CUDA BF16; không dùng FP16.

## Kết quả regression DAVIS

Đã chạy 1.206 lượt tìm ảnh: 201 query × 2 chế độ × 3 cấu hình. Bảng dưới chỉ lấy nhóm **object test**, tách khỏi dev và scene. “Đúng” yêu cầu cả video và mốc nằm trong khoảng ground truth.

| Lấy mẫu / cách tìm | Tổng frame | Query dương có frame GT | Đúng top 1 / 42 | Đúng top 5 / 42 | Từ chối query dương / 42 | Trả kết quả cho query vắng / 18 |
|---|---:|---:|---:|---:|---:|---:|
| Đều 0,1 fps / tương tự | 5 | 3 | 3 | 3 | 0 | 18 |
| Đều 0,1 fps / đối chiếu | 5 | 3 | 3 | 3 | 39 | 0 |
| Hybrid 0,1 fps / tương tự | 17 | 42 | 42 | 42 | 0 | 18 |
| Hybrid 0,1 fps / đối chiếu | 17 | 42 | 27 | 27 | 15 | 0 |
| Đều 1 fps / tương tự | 40 | 42 | 41 | 42 | 0 | 18 |
| Đều 1 fps / đối chiếu | 40 | 42 | 25 | 25 | 17 | 0 |

Không có ngưỡng loại kết quả trong chế độ tương tự, nên nó luôn trả ứng viên ngay cả với ảnh vắng. Chế độ đối chiếu đã chặn các truy vấn vắng này, nhưng đánh đổi 15/42 hoặc 17/42 query dương bị từ chối khi đã có frame GT trong chỉ mục. Những kết quả đó chưa đủ để đặt đối chiếu làm mặc định cho tìm đối tượng đổi góc. Với hybrid, các nhóm bị từ chối gồm lợn, xe chuyển động/bóng xe và một số con cừu trong nhóm; không chỉ các trường hợp bị thiếu frame.

Ở nhóm **scene test** (24 dương, 18 vắng), hybrid tương tự đúng top 5 là 24/24; đối chiếu còn 17/24 và từ chối cả 18 query vắng. Đều 1 fps tương ứng 24/24 và 16/24. Kiểm tra ngôn ngữ tự nhiên đạt top 1 đúng nguồn/GT 6/8 với đều 0,1 fps, 8/8 với hybrid 0,1 fps và đều 1 fps. Đây vẫn là kiểm tra nhỏ trên bộ đã xem, không là benchmark ngôn ngữ tổng quát.

[JSON tổng hợp](../results/sampling-verification-20261102.json) và [CSV toàn bộ query](../results/sampling-verification-20261102-queries.csv) giữ ca sai, nhãn và các hit để kiểm tra lại. Sau phép đo này, nhánh chọn thứ tự của `moments.py` được sửa để không đếm các cảnh điểm thấp; các phép đo trên không truyền `occurrence`, nhánh truy hồi thông thường không thay đổi. Hash source tại lần đo được giữ nguyên trong report; hash của bản có sửa thứ tự nằm trong report video thực tế.

## Kết quả video 2 giờ 11 phút

Đã xử lý đủ 7.886,3 giây, 1080p/60 fps thành **4.355 khung**: 3.944 anchor mỗi 2 giây và 411 khung bổ sung. Không có lỗi index, không trùng timestamp, không thiếu thumbnail/detail và không có frame nằm ngoài shot đã lưu. Một khoảnh khắc đã lưu được giữ nguyên; thư viện cũ 789 khung vẫn còn để đối chứng. Cache ảnh chi tiết mới chiếm 518.637.478 byte (khoảng 519 MB).

Bộ dò tạo 513 đoạn, trung vị dài 1 giây. Lịch đều mỗi 10 giây có frame trong 103 đoạn; mỗi 2 giây có trong 293 đoạn; hybrid có trong cả 513. Đây là độ phủ **đoạn do detector phân chia**, không phải 513 cảnh đã được con người gán nhãn. Đổi UI hoặc chớp sáng có thể tạo đoạn ngắn.

Không query nào trong 18 ảnh trùng đúng frame index. Kết quả tìm lại **mốc nguồn trong ±3 giây**:

| Cách tìm | Toàn ảnh top 1 / 9 | Toàn ảnh top 5 / 9 | Crop top 1 / 9 | Crop top 5 / 9 | Ảnh ngoài nguồn có kết quả / 6 |
|---|---:|---:|---:|---:|---:|
| Đều mỗi 10 giây, tương tự | 3 | 4 | 1 | 2 | 6 |
| Đều mỗi 2 giây, tương tự | 5 | 7 | 0 | 1 | 6 |
| Mỗi 2 giây + cut, tương tự | 5 | 7 | 0 | 1 | 6 |
| Mỗi 2 giây + cut, đối chiếu | 7 | 9 | 3 | 3 | 0 |

Với 9 mốc này, chưa thấy tăng số query trúng top 5 khi thêm 411 frame so với mỗi 2 giây. Cải thiện tìm lại toàn cảnh từ 4/9 lên 9/9 đến từ **cả lịch dày hơn và bước đối chiếu**, không được gán hết cho bổ sung theo cut. Sáu ảnh ngoài nguồn khá khác gameplay; 0/6 trả kết quả chưa chứng minh đã giải quyết các negative khó cùng giao diện game.

Nguyên nhân crop yếu nằm ngay ở bước tạo ứng viên: toàn ảnh có mốc nguồn trong top 48 ở 9/9 query, crop chỉ có 3/9. Hạng raw tốt nhất của mốc nguồn ở chín crop lần lượt là **1386, 70, 4, 18, 12, 129, 153, 1044, 54**. Tăng độ chặt của verifier không sửa được việc frame đúng không vào tập ứng viên. Một crop còn thiếu keypoint nên trả trạng thái thiếu chi tiết. Hướng cần đo tiếp là chỉ mục vùng/ứng viên theo vùng ảnh và negative khó cùng domain, giữ một tập kiểm tra mới; chưa triển khai hay tuyên bố hiệu quả của hướng đó trong lượt này.

Đã xem trực tiếp ca crop ở 125,35 giây: trả các màn hình danh sách người chơi giống nhau tại 290, 302 giây và các mốc khác. Một hit ở 122 giây cũng nằm ngoài dung sai 3 giây dù rất gần. Kết quả này minh họa vì sao tìm lại mốc gốc khác với tìm mọi lần nội dung tương tự xuất hiện; không suy ra danh tính nhân vật từ dấu “đã đối chiếu”.

Ba truy vấn tiếng Việt đều trả kết quả và mở được ảnh. Xem top 1 cho thấy “căn phòng có đèn xanh” phù hợp về hình ảnh; “màn hình bỏ phiếu” tại 6.670 giây lại là màn hình thông báo vai trò/lobby, nên **chưa đúng ý định**. “Logo trên nền đen” tại 4.558 giây chủ yếu là nền đen với watermark nhỏ và webcam; không chứng minh tìm đúng một logo cụ thể. Chức năng ngôn ngữ tự nhiên được giữ, độ chính xác ngữ nghĩa vẫn cần cải thiện.

Thời gian API của 24 query: tương tự trung vị 784,5 ms (370–1.838 ms); đối chiếu trung vị 10.953 ms (116–28.161 ms). Ca 116 ms từ chối sớm vì thiếu chi tiết; chế độ đối chiếu chạy sau truy vấn tương tự nên được hưởng cache query vector. Máy còn chạy các tác vụ kiểm tra/đóng gói, nên đây là số đo quan sát, không phải benchmark tốc độ cô lập hoặc so sánh lạnh/ấm công bằng. Đối chiếu đang chậm hơn đáng kể, không có tuyên bố tối ưu tốc độ hoàn tất.

[Report đầy đủ](../results/real-video-sampling-20261102.json) giữ từng query, xếp hạng, độ phủ ứng viên và thời gian. Lab riêng tư phục vụ tại `http://127.0.0.1:1420/sampling-real-20261102/`; ảnh chỉ ở thư mục ignored `desktop/dist/sampling-real-20261102/`.

## Kiểm chứng kỹ thuật

- 37 ca backend/công thức đo qua. Có cảnh 0,3 giây nằm giữa các mốc đều, hủy quét không ghi cache hoàn tất, pause/resume không trùng frame, đoạn không vượt cut, ảnh không liên quan/ít chi tiết không được xác nhận, và thứ tự bỏ qua cảnh điểm thấp.
- 7 luồng Playwright qua, gồm đổi chế độ ảnh, báo thiếu bằng chứng, giữ tìm văn bản và cảnh báo lập chỉ mục lại. Fixture encoder dùng cho UI không phải số đo EG2.
- TypeScript và frontend production build qua. Bản Windows native build qua; frontend đóng gói chỉ gồm `index.html` và hai asset JS/CSS, khớp bản phục vụ app và không chứa thư mục lab.
- Playwright trên thư viện video thật qua: hai chế độ ảnh, tìm tiếng Việt, mở video 1920 px đúng mốc đang dừng, đọc Range 206, lưu rồi bỏ riêng khoảnh khắc thử nghiệm, giữ khoảnh khắc cũ. Clip xuất từ nguồn thật giải mã được, dài đúng 2,0 giây. Không mở cửa sổ native.
- Lab qua 96 trạng thái query/cách tìm; toàn bộ ảnh giải mã được, không lỗi JavaScript hoặc tràn ngang ở 920 px. Đã xem ảnh chụp app thật và các khung đúng/sai.
- Runtime CPU và runtime CUDA đóng gói đều chạy EG2 thật, tìm ảnh/văn bản, kiểm tra xác thực và xuất clip. Bản CUDA mới có source khớp workspace, ZIP CRC hợp lệ và 17 file engine khớp byte với source. Không chứa trọng số, video, DB hoặc lab riêng tư. Chưa chạy cửa sổ native trong lượt này để không làm gián đoạn người dùng.

Bản portable CUDA mới: `outputs/releases/FrameAtlas_0.1.0_20261102_windows-x64-cuda126-portable.zip`, 3.449.246.618 byte. SHA-256: `bbc3c30e7c47827b9634646c7708cc912641cc0a116973c1b09bb18437637f08`. Thư mục chạy trực tiếp là `outputs/releases/FrameAtlas-CUDA-20261102/`; runtime và engine phải đi cùng executable. [Bằng chứng kỹ thuật đã bỏ đường dẫn riêng tư](../results/desktop-sampling-checks-20261102.json).

Lần quét toàn bộ video thành công mất 857,12 giây trên máy này. Đây là một lần chạy có các công việc nền khác; không dùng làm tuyên bố tăng tốc. Timeout quét dựa trên thời gian thực thi không có tiến triển, thay vì cắt mọi video sau một giờ hoặc coi laptop ngủ là lỗi.

## Chạy lại

Các đầu vào model/video/DAVIS phải có sẵn cục bộ. Dùng thư mục output mới cho mỗi lần đo. Script chất lượng video yêu cầu thư viện riêng đã index xong; không mở `Library` trên DB đang chạy chỉ để đọc số liệu.

```powershell
python scripts/evaluate_sampling_verification.py --dataset data/davis-quality/pilot-v1 --model data/models/embeddinggemma-2 --output <fresh-regression-output>
python scripts/prepare_real_video_queries.py --source-metadata outputs/real-video/source.json --protocol docs/lab/real-video-sampling-protocol.json --output <fresh-query-output>
python scripts/evaluate_real_video_sampling.py --session <private-panel-session.json> --queries <query-output> --davis data/davis-quality/pilot-v1 --model data/models/embeddinggemma-2 --output <fresh-real-output>
```

File session chứa token cục bộ, không được chia sẻ. `scripts/build_real_video_review.py` dựng lab riêng tư từ report và thumbnail. `scripts/verify_sampling_ui.cjs` kiểm tra app thực qua Playwright headless, không mở cửa sổ native hoặc tự phát âm thanh.

## Cơ sở kỹ thuật

- [FFmpeg scdet](https://ffmpeg.org/ffmpeg-filters.html#scdet): quét biến đổi cảnh; đã đối chiếu các tùy chọn với `ffmpeg -h filter=scdet` và `-h filter=metadata` của runtime thực tế.
- [OpenCV feature matching](https://docs.opencv.org/4.x/dc/dc3/tutorial_py_matcher.html) và [homography](https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html): kiểm tra tương ứng chi tiết/hình học, không chứng minh danh tính chung của vật thể.

Các thư viện này đã có trong runtime; không thêm model hoặc dịch vụ mạng cho bước đối chiếu.
