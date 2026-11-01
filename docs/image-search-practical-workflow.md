# Tìm hình ảnh trong video: luồng thực tế và kiểm chứng đầu vào

Ngày 01/11/2026. Người dùng xác nhận đề tài chính là **xây dựng hệ thống tìm kiếm hình ảnh trong video**, ưu tiên làm chính xác; các hướng khác là mở rộng.

## Công việc thực tế được chọn

Người dùng có một ảnh chụp màn hình hoặc ảnh chi tiết, cần tìm lại video nguồn và thời điểm để xem hoặc lấy tư liệu. Luồng: chọn thư viện → tải ảnh → chọn toàn cảnh hoặc một vùng → duyệt kết quả tại timestamp → kiểm tra đoạn nguồn → lưu/xuất clip. Có thể phục vụ editor hoặc thư viện video cá nhân mà chưa cần chuyển sang phân tích cảm xúc, chấm nói hay nhận diện danh tính.

Hai ý định cần giữ khác nhau: tìm lại **cảnh gốc của screenshot** và tìm **những cảnh có đối tượng trong crop**. Ảnh toàn cảnh giữ nhiều thông tin về bối cảnh; crop tập trung vào chi tiết và có thể khớp ở bối cảnh khác. Không mặc định thứ hạng khác sau crop là tốt hơn hoặc xấu hơn nếu chưa xác định ý định và ground truth.

## Lựa chọn triển khai trong lượt này

Đã cân nhắc thay encoder, thêm chỉ mục vùng/reranker, hoặc hoàn thiện đầu vào ảnh và phép kiểm chứng. Chọn cách cuối trước: model và chỉ mục giữ nguyên để phân biệt lỗi xử lý ảnh với giới hạn retrieval. Đây là lựa chọn triển khai của agent trong phạm vi người dùng đã giao, không phải một kết quả benchmark chứng minh crop luôn tốt hơn.

- Xem ảnh tham chiếu và khoanh vùng bằng chuột hoặc các ô phần trăm dùng được bằng bàn phím.
- Áp dụng crop ở độ phân giải nguồn, PNG lossless; có ảnh xem trước của vùng thực sự gửi đi và nút khôi phục toàn ảnh.
- Khi vùng chưa áp dụng, chặn tìm kiếm; khi đổi ảnh/vùng, xóa kết quả cũ. Giới hạn kích thước/diện tích ảnh tại đầu vào.
- Sửa ảnh EXIF: giải mã theo hướng hiển thị trước khi chuyển RGB và encode. Không thay tiền xử lý frame trong chỉ mục nên không cần lập chỉ mục lại vì sửa này.

Tham khảo API: [Pillow exif_transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose), [Canvas drawImage](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/drawImage). Không thêm thư viện frontend hoặc model mới.

## Kiểm chứng đã thực hiện

1. **Tái hiện lỗi EXIF trước khi sửa:** hai ca ảnh lật ngang và xoay 90° có cùng nội dung hiển thị nhưng bộ xử lý bỏ hướng EXIF, khiến truy hồi fixture chọn sai video. Cả hai ca thất bại trước sửa, qua sau sửa. Fixture chỉ kiểm tra hình ảnh mà API chuyển tới encoder, không đại diện chất lượng EG2.
2. **Backend:** 21 ca kiểm thử qua, gồm tìm kiếm, lưu/xuất, phục hồi, lọc thời gian và hai ca EXIF.
3. **Giao diện:** 6 luồng Playwright qua. Ca ảnh có vùng đỏ trên nền xanh: toàn ảnh trả video xanh; crop vùng đỏ gửi ảnh đúng 64 × 180 pixel và trả video đỏ; khôi phục toàn ảnh trả video xanh. Kéo ngược hướng cũng hoạt động; không tràn ngang ở cửa sổ 920 px. Kiểm tra axe WCAG A/AA tự động không có vi phạm trong luồng được kiểm tra.
4. **EG2 thật qua API source mới:** `scripts/verify_image_query_orientation.py` dùng SQLite backup từ kết nối chỉ đọc để tạo bản sao riêng, không khởi tạo worker trên thư viện đang dùng. Với 789 frame và CUDA BF16, ảnh JPEG EXIF xoay và PNG có cùng pixel hiển thị trả cùng 10 kết quả và điểm. Mốc đầu 2.100 s. Đây là kiểm chứng chuẩn hóa đầu vào, không là benchmark accuracy.
5. **Giao diện thật + video người dùng:** ảnh tham chiếu ở 2.102,75 s trả mốc đầu 2.100 s khi dùng toàn ảnh. Crop 13% rộng × 25% cao, tại x=46%, y=40%, lấy avatar hoạt hình và thú đi kèm, trả các mốc đầu 7.010 s, 490 s, 1.220 s, 860 s, 1.390 s. Đã xem hai thumbnail đầu, thấy avatar có ngoại hình tương ứng cùng thú màu hồng; chưa gán nhãn toàn bộ lần xuất hiện hoặc xác nhận danh tính người điều khiển. Trình phát mở 7.010 s, 1920 px, đang dừng. Không suy ra recall/precision từ ca này.

Bằng chứng riêng tư ở `outputs/image-query-lab/`: `orientation-report.json`, `real-ui-report.json`, `real-image-crop.png`, `top-crops/`. Không commit hình/video, snapshot DB hoặc token. Bản tóm tắt số liệu đã bỏ đường dẫn nằm trong `results/image-query-input-verification-20261101.json`.

Frontend trong tab local đã được build lại; các gói portable trước đó chưa được đóng gói lại trong lượt này. API EXIF được kiểm chứng trên source workspace mới; worker portable đang chạy có thể vẫn giữ code cũ cho đến khi nâng cấp/khởi động lại. Không thay hoặc khởi tạo lại thư viện live để chạy thử.

## Chất lượng cần đo tiếp trước khi mở rộng

- Tập ảnh toàn cảnh/crop từ video thật, có nhãn khoảng xuất hiện và video không chứa đối tượng. Giữ tập test riêng; tránh dùng đúng frame đã index hoặc các bản sao gần nhau làm bằng chứng tổng quát hóa.
- Đo riêng tìm cảnh gốc, tìm đối tượng ở cảnh khác, chi tiết nhỏ, thay góc/ánh sáng và truy vấn không có kết quả. Báo tỷ lệ trúng top-k, bỏ sót, nhận nhầm và sai lệch thời gian.
- So toàn frame với chỉ mục vùng hoặc kiểm tra lại vùng trên cùng tập cố định. Rerank top-k không thể cứu trường hợp cảnh đúng đã bị bỏ khỏi tập ứng viên; phải đo cả bước tạo ứng viên.
- Chỉ mục video thật hiện mỗi 10 giây mới có một frame. Các cảnh ngắn giữa hai mốc chưa được quan sát; không thể sửa giới hạn này bằng đổi ngưỡng cosine. Đo lấy mẫu dày hơn hoặc bổ sung theo chuyển cảnh trước khi hứa tìm đủ lần xuất hiện.
- Trạng thái “không tìm thấy” cần hiệu chỉnh bằng truy vấn âm đúng domain. Không đặt một ngưỡng tùy ý rồi gọi kết quả trên ngưỡng là chắc chắn đúng.

Thước đo sản phẩm là người dùng tìm được đúng đoạn và mất ít thời gian duyệt/sửa hơn. Tốc độ model, khả năng mở app và các fixture màu chỉ xác nhận từng phần kỹ thuật.
