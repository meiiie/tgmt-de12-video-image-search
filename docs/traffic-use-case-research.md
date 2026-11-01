# Hướng ứng dụng thực tế: rà soát phương tiện và sự cố từ camera

Ngày nghiên cứu: 01/11/2026. Trạng thái: đề xuất sản phẩm và kế hoạch kiểm chứng; **chưa triển khai nhận diện xe hay phát hiện sự cố trong FrameAtlas**.

## Quyết định đề xuất

Phát triển FrameAtlas thành **ứng dụng desktop giúp bảo vệ hoặc người quản lý cổng trường, bãi xe, kho tìm lại phương tiện và rà soát sự cố trong video camera đã ghi**.

Một công việc trọn vẹn: nhập bản ghi → tìm xe/sự kiện → xem diễn biến trước và sau → xác nhận hoặc loại bỏ → xuất clip kèm thời gian và ghi chú. Giá trị cần đo là giảm thời gian tìm đủ bằng chứng và giảm bỏ sót, không phải số lượng khung hình có bounding box.

Hai khả năng đầu tiên:

1. **Tìm phương tiện bằng ảnh hoặc mô tả**, có lọc camera, khoảng thời gian và vùng đi qua. Đây là phần phù hợp trực tiếp với EG2 và Đề 12.
2. **Rà soát xe đi sai chiều qua cổng một chiều đã cấu hình**, dựa trên quỹ đạo xe qua các vùng/vạch theo thời gian. Người dùng xem và xác nhận từng đề xuất.

Tiếp theo mới thêm xe dừng lâu tại vùng cần giữ thông thoáng. Cần phân biệt dừng, di chuyển chậm, đợi mở cổng và hàng xe ùn lại. Không mặc định mọi xe hiện diện lâu đều vi phạm.

Khách hàng ban đầu là giả thuyết: đơn vị nhỏ đã có camera và xuất được MP4 nhưng còn tua tay khi có phản ánh. Chưa có phỏng vấn hoặc thử nghiệm tại đơn vị Việt Nam để chứng minh tần suất nhu cầu, khả năng trả tiền hay hiệu quả thực tế.

## Tại sao chọn bài toán này

| Hướng | Việc người dùng cần hoàn thành | Liên hệ với EG2 | Quyết định |
|---|---|---|---|
| Tìm cảnh trong vlog/game | Tìm lại cảnh để dựng video | Trực tiếp | Giữ khả năng nền; chưa phải tình huống ưu tiên mới |
| Tìm xe và rà soát sự cố tại một địa điểm | Xử lý phản ánh, tìm đoạn camera, ghi nhận diễn biến | Trực tiếp cho tìm kiếm; thêm tracking cho hành vi | **Ưu tiên**: đầu ra và người dùng rõ, tận dụng phần desktop đã làm |
| Tự động nhận diện mọi vi phạm đường phố | Xác định nhiều loại hành vi trong điều kiện giao thông phức tạp | Chỉ là một phần nhỏ | Phạm vi quá rộng cho lần kiểm chứng đầu |
| Phân tích an toàn kho: người/xe nâng, vùng cấm, tình huống suýt va chạm | Rà soát hoạt động và nguy cơ tại nơi làm việc | Tìm sự kiện, cần thêm dữ liệu/chuyên môn về khoảng cách và chuyển động | Hướng mở rộng sau khi pipeline cơ bản có bằng chứng |

Đây là nhận định thiết kế của dự án, không phải bảng xếp hạng thị trường.

Nhu cầu rà soát sự cố có căn cứ vận hành: tài liệu NYSDOT yêu cầu phát hiện xe sai chiều, thông báo và để nhân viên xác nhận cảnh báo. Đó là đặc tả mua sắm hệ thống giao thông lớn, không chứng minh nhu cầu mua ứng dụng của khách hàng nhỏ tại Việt Nam. [NYSDOT](https://www.dot.ny.gov/spec-repository-us/683.03080010.pdf)

Caltrans nêu vấn đề nhân viên phải kiểm tra camera khi có thông tin sự cố và nguy cơ bỏ qua hệ thống khi báo giả quá nhiều. Báo cáo năm 2019 này là tổng hợp nghiên cứu sau khi phạm vi triển khai bị thay đổi; không dùng nó như bằng chứng một pilot đã thành công. [Caltrans AVID](https://dot.ca.gov/-/media/dot-media/programs/research-innovation-system-information/documents/research-results/task2531-rrs-5-19-a11y.pdf)

Hướng cổng/kho cũng có cơ sở về vận hành: HSE khuyến nghị tổ chức tuyến một chiều để giảm nhu cầu lùi xe. Đây là tài liệu an toàn nơi làm việc của Anh, dùng để hiểu vấn đề; không suy diễn thành quy định pháp luật Việt Nam hoặc lời hứa rằng phần mềm hậu kiểm phòng ngừa được tai nạn. [HSE](https://www.hse.gov.uk/workplacetransport/information/reversing.htm)

## Một tình huống sử dụng cụ thể

Ví dụ giả định để xác định sản phẩm, chưa phải sự kiện đã quan sát:

> Bảo vệ nhận phản ánh: khoảng 15–16 giờ có một xe tải trắng đi vào bằng cổng dành cho xe ra. Có hai file camera dài tổng cộng tám giờ và một ảnh chụp xe, chưa đọc được biển số.

1. Nhập bản ghi, đặt camera và mốc giờ bắt đầu nếu nguồn chưa có metadata đáng tin cậy. Giữ riêng thời gian trong file và giờ thực tế; không tự suy ra giờ quay từ giờ sửa file.
2. Trên camera cố định, đánh dấu vùng cổng và chiều được phép. Xem thử vài lượt đi đúng để kiểm tra cấu hình.
3. Nhập ảnh xe hoặc câu “xe tải trắng”; chọn khoảng 15–16 giờ. Ảnh trả về là các xe ứng viên tương tự, chưa phải khẳng định cùng một chiếc xe.
4. Chọn bộ lọc “qua cổng sai chiều”. Ứng dụng kết hợp ứng viên tìm kiếm với sự kiện hình học; hiển thị xe đi qua vạch nào trước, vạch nào sau, kèm khoảng thời gian.
5. Mở clip có ngữ cảnh trước và sau. Đánh dấu “xác nhận”, “không đúng” hoặc “chưa đủ dữ liệu”. Không chuyển một điểm similarity thành phần trăm chắc chắn vi phạm.
6. Xuất clip, ảnh minh họa, camera, thời gian nguồn, ghi chú và tham chiếu file gốc. Một hồ sơ có thể chứa nhiều đoạn; không ép một ảnh tĩnh thay cho diễn biến.

Nếu chỉ có một video ngắn, tua tay có thể nhanh hơn lập chỉ mục. Giá trị tăng khi cần kiểm tra nhiều file hoặc thường xuyên tra cứu lại một thư viện; phép thử phải tính cả chi phí nhập và xử lý lần đầu.

## EG2 giải quyết phần nào

| Yêu cầu | Cách xử lý đề xuất | Giới hạn phải hiện rõ |
|---|---|---|
| “Xe tải màu trắng”, “xe máy chở thùng” | EG2 tìm trên ảnh cắt phương tiện và khung ngữ cảnh; gộp theo track | Xe giống nhau vẫn có thể bị lẫn; tiếng Việt cần đo riêng |
| Tìm xe tương tự ảnh mẫu | Embedding ảnh, lọc thời gian/camera, xem lại chuỗi xuất hiện | Tương đồng hình ảnh không chứng minh danh tính xe |
| Xe đi sai chiều | Detector + tracker + thứ tự qua vạch/vùng trong cấu hình camera | Mất track, camera rung, xe quay đầu hoặc lùi đỗ phải được xử lý |
| Xe dừng lâu trong vùng | Thời gian hiện diện và độ ổn định vị trí, có xử lý mất dấu | Không chỉ đếm số khung xuất hiện; phân biệt hàng chờ |
| Vượt đèn đỏ | Trạng thái đèn đúng hướng + vạch dừng + thời điểm xe vượt vạch | Chưa đưa vào bản đầu; ảnh thấy xe và đèn đỏ là chưa đủ |
| Tốc độ km/h | Đo đạc/hiệu chuẩn mặt đường và timestamp chính xác | Chưa đưa vào bản đầu; độ dịch chuyển pixel không phải km/h |
| Biển số | Pipeline OCR riêng, ảnh đủ chi tiết, người xem xác nhận | EG2 không thay OCR; chưa có OCR trong ứng dụng |

Các điều kiện ở trên là phân tích kỹ thuật cho thiết kế, chưa phải khả năng đã kiểm chứng của app. Frigate cũng yêu cầu kích thước thực khi ước lượng tốc độ từ vùng camera. [Frigate zones](https://docs.frigate.video/configuration/zones/)

Pipeline dự kiến:

```text
Video camera + thời gian nguồn + cấu hình vùng/chiều
    → phát hiện xe → theo dõi từng xe → đoạn xuất hiện và quỹ đạo
        → luật theo thời gian: sai chiều, dừng lâu
        → ảnh xe/ngữ cảnh → EG2 → tìm bằng chữ hoặc ảnh
    → lọc và xếp hạng → xem video → xác nhận → xuất hồ sơ
```

Luật thời gian và tìm kiếm có thể hoạt động độc lập. Tìm xe không yêu cầu xe phải có sự kiện bất thường; cảnh báo sai chiều không phụ thuộc người dùng gõ đúng mô tả.

## Nghiên cứu nguồn mở: học gì, khác ở đâu

| Dự án | Điều đã xác nhận từ nguồn gốc | Cách dùng cho dự án |
|---|---|---|
| [Frigate semantic search](https://docs.frigate.video/configuration/semantic_search/) | Tìm đối tượng được theo dõi bằng ảnh/chữ; embedding chạy cục bộ | Đối chiếu trực tiếp, tránh coi tìm kiếm camera bằng AI là tính năng mới |
| [Frigate zones](https://docs.frigate.video/configuration/zones/) | Vùng, thời gian hiện diện, chống dao động ở ranh giới | Tham khảo cách cấu hình và biểu diễn sự kiện; không sao chép nguyên kiến trúc NVR |
| [ByteTrack](https://github.com/FoundationVision/ByteTrack/) | Tracker chính chủ, mã MIT; liên kết detections thành track | Ứng viên baseline tracking; không lấy tốc độ trên V100/MOT17 làm tốc độ máy người dùng |
| [RT-DETR](https://github.com/lyuwenyu/RT-DETR/) | Detector chính chủ, mã Apache-2.0, có hướng triển khai ONNX/TensorRT/OpenVINO | Thử một biến thể nhỏ trên xe máy/ô tô của camera đích trước khi chốt model |
| [CityFlow-NL](https://github.com/fredfung007/cityflow-nl) | Bài toán xếp hạng track theo mô tả, baseline và cấu trúc nhãn | Đánh giá phần tìm kiếm độc lập với lỗi detector/tracker |
| [CVAT track mode](https://docs.cvat.ai/docs/annotation/manual-annotation/modes/track-mode-basics/) | Gán nhãn track và nội suy giữa keyframe | Chuẩn bị nhãn thật, sửa mất dấu/đổi ID; không tự viết lại công cụ gán nhãn |

**Lợi thế dự kiến cần kiểm chứng:** người dùng Windows mở bản ghi có sẵn, không phải thiết lập hệ thống ghi hình mới; thao tác tập trung vào tìm, xem, đánh dấu và xuất hồ sơ. Hoạt động offline phù hợp nguồn camera cần giữ nội bộ. Frigate đã làm nhiều chức năng liên quan; chưa có cơ sở khẳng định FrameAtlas tốt hơn nó về chất lượng, tốc độ hoặc vận hành dài hạn.

Khi người dùng cần giám sát RTSP liên tục, nên đánh giá tích hợp với NVR có sẵn. Bản đầu xử lý bản ghi để kiểm chứng chất lượng và quy trình; chưa hứa cảnh báo trực tiếp cứu nguy tức thời.

Giấy phép mã, trọng số và dữ liệu là ba phần riêng. MIT/Apache của repository không tự cấp quyền thương mại cho mọi model/dataset được dùng cùng nó.

## Video nào để thử thật

| Nguồn | Phù hợp kiểm tra | Không chứng minh được |
|---|---|---|
| [CityFlow-NL / AI City 2023 Track 2](https://github.com/fredfung007/cityflow-nl) | Tìm xe theo mô tả trên track có nhãn; repo mô tả 2.155 track train, 184 ứng viên test | Không tự có nhãn mọi vi phạm; track chuẩn đã cho sẵn khác pipeline tự phát hiện |
| [UA-DETRAC](https://arxiv.org/html/1511.04136v4) | Phát hiện/theo dõi xe: 100 video, hơn 140.000 khung có nhãn | Nhãn box/track không đồng nghĩa nhãn sai chiều hoặc vượt đèn đỏ |
| [AI City 2021 Track 4](https://www.aicitychallenge.org/2021-challenge-tracks/) | Sự cố như xe chết máy, va chạm trong camera giao thông | Không phải bộ kiểm chứng đầy đủ cho quy tắc cổng riêng |
| [UIT-ADrone](https://uit-together.github.io/datasets/UIT-ADrone/) | Giao thông Việt Nam, nhiều xe máy, các loại bất thường; 51 video, khoảng 6,5 giờ | Góc drone và chuyển động camera khác camera cố định; nhãn bất thường theo frame không tự cung cấp mọi nhãn hành vi theo từng xe |
| Bản ghi được phép sử dụng từ cổng trường/bãi xe/kho | Quy trình người dùng và sự kiện tại địa điểm đích | Một góc quay ban ngày không đại diện mọi camera/đêm/mưa |

Trang [AI City Dataset Access](https://www.aicitychallenge.org/ai-city-challenge-dataset-access/) hiện công bố một số bộ dữ liệu không còn yêu cầu biểu mẫu/password. Đây là thông tin về truy cập, không phải giấy phép dùng thương mại. [Thỏa thuận dữ liệu 2021](https://www.aicitychallenge.org/wp-content/uploads/2021/01/DataLicenseAgreement_AICityChallenge_2021.pdf) giới hạn sử dụng sau cuộc thi cho nghiên cứu học thuật phi thương mại và hạn chế phân phối. Phải kiểm tra điều khoản đúng từng bản dữ liệu trước khi huấn luyện/đóng gói sản phẩm.

Đã đọc trang nguồn; **chưa tải và kiểm tra byte các video/dataset** trong lượt nghiên cứu này. Điều khoản khai thác UIT-ADrone chưa được xác nhận đủ từ trang đã đọc. Không đưa video mẫu hoặc weights vào bản phát hành chỉ vì có đường dẫn tải.

Hai hướng mới có ích để theo dõi, chưa chọn làm nền:

- [AI City 2026 Track 3](https://www.aicitychallenge.org/2026-track3/) có bài toán hiểu bất thường trong CCTV. Nhãn train được sinh bằng VLM, test được con người xác minh; video lấy từ nhiều nguồn với điều khoản riêng. Không dùng nhãn tự sinh như kết luận đã được con người chứng thực.
- [Nghiên cứu CCTV Đà Nẵng, công bố 08/05/2026](https://www.techscience.com/cmc/v88n1/67301) mô tả dữ liệu ảnh giao thông địa phương. Hữu ích để nghiên cứu chênh lệch miền; dữ liệu ảnh detection chưa thay thế video liên tục có nhãn sự kiện. Chưa kiểm chứng đường tải/giấy phép của bộ này.

**Lựa chọn thực hành:** CityFlow-NL cho thí nghiệm retrieval có đối chứng; một camera cố định tại cổng cho phép thử vận hành. UIT-ADrone là bài kiểm tra bổ sung về giao thông Việt Nam sau đó, không lấy vùng vẽ cố định áp thẳng lên video drone đang dịch chuyển.

Video game người dùng đã cung cấp vẫn hữu ích cho kiểm thử file dài, tiến độ, tiếp tục xử lý và xuất clip. Nó không kiểm chứng khả năng giao thông.

## Phạm vi bản đầu có thể kiểm chứng

### Dữ liệu và giao diện

- Nhập MP4 của một camera cố định; lưu tên camera, múi giờ, mốc bắt đầu do người dùng khai báo và nguồn thông tin thời gian. Nhiều file liên tiếp có khoảng hở phải hiện khoảng hở.
- Vẽ vùng cổng, hai vạch có thứ tự và chiều cho phép. Cấu hình có phiên bản; sự kiện giữ phiên bản đã dùng để có thể giải thích kết quả.
- Mỗi xe có đoạn xuất hiện, ảnh đại diện, đường đi và khung ngữ cảnh. Gộp kết quả theo track để tránh hàng chục ảnh cùng một lượt xe.
- Kết quả tìm và sự kiện có đủ trạng thái đang xử lý, chưa có kết quả, chưa đủ dữ liệu, đã xác nhận, đã loại bỏ. Không coi “không thấy sự kiện” là “đã chứng minh không có sự kiện”.
- Hồ sơ xuất có clip, mốc file nguồn, thời gian thực nếu đã xác định, ghi chú và hash để phát hiện file bị thay đổi. Hash không tự chứng minh nguồn camera hay giá trị pháp lý của nội dung.

### Logic sự kiện đầu tiên

Xe đi sai chiều được đề xuất khi một track hợp lệ đi qua hai vạch theo thứ tự ngược cấu hình, trong vùng cổng và trong khoảng thời gian hợp lý. Dùng timestamp để đo thời gian, không mặc định fps nguồn luôn đều. Chống rung vị trí ở ranh giới; gộp một lượt xe thành một sự kiện.

Các trường hợp cần kiểm tra riêng: xe lùi đỗ ngoài cổng, quay đầu, dừng giữa hai vạch, nhiều xe che nhau, mất/đổi track ID, camera rung/đổi góc, cắt file giữa sự kiện, video thiếu khung. Khi camera đổi góc, cấu hình vùng cũ không còn hợp lệ; cần đánh dấu mất hiệu lực thay vì tiếp tục kết luận.

### Hạ tầng

Giữ Tauri + React và worker Python hiện tại trong lần thử đầu. Thêm detector nhỏ/tracker và lập chỉ mục EG2 từ ảnh đại diện theo track. Benchmark ONNX Runtime hoặc backend hiện có trước khi chọn. Không chuyển sang Go chỉ dựa trên kỳ vọng nhanh hơn: cần đo giải mã video, inference, lưu trữ và độ trễ tìm kiếm trên đúng máy.

Máy hiện tại có RTX 3050 Ti 4 GB. Đo bộ nhớ khi detector và EG2 cùng hoạt động; nếu không đủ thì tách giai đoạn tạo track và tạo embedding, giữ tiến độ/checkpoint. Không hứa số luồng camera realtime khi chưa có phép đo.

Chế độ đã thử trước đây 0,1 fps tương đương một ảnh mỗi 10 giây, có thể bỏ qua toàn bộ một lượt xe. Pipeline tracking phải có nhịp lấy mẫu riêng; khảo sát 5/10 fps chỉ là điểm khởi đầu thí nghiệm, chọn theo tốc độ xe, khoảng nhìn và kết quả bỏ sót. Không coi số đo EG2 trên video game là tốc độ pipeline giao thông.

## Đo thế nào để biết sản phẩm có ích

Các con số sau là **mục tiêu pilot đề xuất, chưa đạt và chưa phải cam kết sản phẩm**.

| Câu hỏi | Phép đo | Mục tiêu pilot ban đầu |
|---|---|---|
| Có tìm lại đúng xe? | Recall@5 và MRR theo track; tách chữ VI, chữ EN, ảnh | Recall@5 ≥ 90% trên ít nhất 50 truy vấn có nhãn; báo riêng từng nhóm |
| Có đánh dấu đúng sai chiều? | Precision/recall theo sự kiện, ghép một-một theo camera, xe và thời gian | Precision ≥ 90%, recall ≥ 90% trên tập giữ lại; tối thiểu 30 sự kiện để có báo cáo sơ bộ |
| Có làm phiền bởi báo giả? | Số sự kiện giả/camera-giờ trên video bình thường dài | ≤ 1/camera-giờ trên ít nhất 10 camera-giờ âm tính; nêu rõ cảnh/ngày/đêm |
| Người dùng làm việc nhanh hơn? | Từ nhận yêu cầu đến xuất đủ đoạn đúng; so với tua tay | Thời gian trung vị giảm ít nhất 50%, không giảm tỷ lệ hoàn thành đúng |
| Máy chịu được không? | Thời gian xử lý/giờ video, p50/p95 truy vấn, RAM/VRAM/disk | Đo trên đúng máy; chưa đặt lời hứa realtime trước baseline |

Ba mươi sự kiện chỉ đủ làm mốc sàng lọc ban đầu, không chứng minh độ tin cậy phổ quát. Báo số đếm TP/FP/FN và khoảng bất định; nếu không đủ dữ liệu thì ghi chưa đủ, không tăng tỷ lệ bằng cách chọn vài clip thuận lợi.

Quy trình đánh giá:

1. Gán nhãn diễn biến và thời gian độc lập trước khi chỉnh ngưỡng. Có cả trường hợp khó và nhiều giờ không có sự kiện. Các hình minh họa hoặc tình huống mô phỏng an toàn chỉ kiểm thử logic, báo tách khỏi video hiện trường.
2. Tách theo camera/ngày hoặc nguyên phiên ghi hình. Không chia ngẫu nhiên khung gần nhau vào train và test. Cấu hình hình học theo camera là thao tác setup được phép; không điều chỉnh ngưỡng bằng nhãn test.
3. Định nghĩa trước cách khớp sự kiện: đúng camera, cùng lượt xe theo người gán nhãn, khoảng dự đoán chứa lần vượt vạch quyết định; chỉ một dự đoán khớp một sự kiện. Các cảnh báo trùng còn lại tính FP. Đo thêm sai lệch thời gian để tránh một đoạn quá dài được coi là định vị tốt.
4. Với tìm ảnh, lấy ảnh truy vấn ở thời điểm khác ảnh đại diện đã index. Báo tách cùng camera và khác camera, không lén biến bài kiểm tra thành tìm đúng ảnh y hệt.
5. So sánh ba baseline: EG2 toàn khung hiện tại; EG2 trên crop theo track; crop + bộ lọc sự kiện. Giữ cùng truy vấn và tập test để xác định phần nào thực sự tạo giá trị.
6. Đo thao tác bằng những nhiệm vụ khác nhau nhưng tương đương; đảo thứ tự dùng app/tua tay để giảm hiệu ứng đã nhớ đoạn. Ghi cả lượt thư viện đã index và lần dùng đầu gồm thời gian nhập/xử lý.
7. Nếu sai chiều không đạt, giữ tìm kiếm + đánh dấu thủ công có ích; không quảng cáo phát hiện tự động. Nếu việc tìm kiếm cũng không tốt hơn tua tay trên tác vụ đích, thu hẹp hoặc đổi bài toán dựa trên kết quả.

## Thứ tự thực hiện tiếp theo

1. Chuẩn bị một tập retrieval công khai có điều khoản phù hợp; lưu nguồn, phiên bản và nhãn. Chạy baseline EG2 hiện có trước khi tích hợp model mới.
2. Thử detector/tracker trên một camera cố định; xem trực tiếp lỗi xe nhỏ, xe máy và đổi ID. Đo tốc độ/bộ nhớ thật.
3. Hoàn thành luồng tìm track → xem đoạn → lưu hồ sơ. Đây là đơn vị sản phẩm hữu ích đầu tiên.
4. Thêm cấu hình hướng qua cổng và hậu kiểm sai chiều, kiểm chứng theo sự kiện trên dữ liệu giữ lại.
5. Pilot với người vận hành; chỉ mở rộng sang dừng lâu, nhiều camera hoặc RTSP khi chất lượng và thời gian thao tác có bằng chứng.

## Phương pháp nghiên cứu và giới hạn nguồn

Dùng Exa với 9 lượt tìm kiếm, mỗi lượt yêu cầu 5 kết quả (45 vị trí kết quả; có các bản khác của cùng tài liệu), theo ba mảng: nhu cầu vận hành, dự án/thuật toán nguồn mở, dữ liệu/đánh giá. Đọc nội dung trích xuất của 16 URL duy nhất qua công cụ fetch. Đây không phải tuyên bố đã đọc trọn 45 công trình hoặc đã chạy các dự án đó.

- Tài liệu cơ quan vận hành cho biết nhu cầu và yêu cầu hệ thống; khác bối cảnh Việt Nam và có nguồn cũ.
- Tài liệu Frigate và các repository do nhóm phát triển công bố là nguồn chính về chức năng; tuyên bố hiệu năng của tác giả không thay benchmark của dự án.
- Trang dataset/paper cho biết nhãn và thiết kế nghiên cứu; khả năng tải đầy đủ, license đúng gói và chất lượng video thực phải kiểm tra tiếp.
- Khả năng bán sản phẩm, tiết kiệm thời gian và chất lượng tiếng Việt vẫn là giả thuyết cần pilot.

Không tải video riêng của người dùng lên dịch vụ ngoài, không mở cửa sổ native và không dùng subagent trong nghiên cứu này.
