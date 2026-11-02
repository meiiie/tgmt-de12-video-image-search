# Lấy mẫu bổ sung ở chuyển cảnh và đối chiếu ảnh

Phạm vi người dùng giao: cải thiện bỏ sót/nhận nhầm, giữ text search, kiểm tra video gameplay đã gửi. Chỉ agent chính thực hiện; mọi tiến trình và kiểm tra UI chạy nền/tab Codex.

## Lựa chọn trước khi đo

- Giữ lựa chọn lấy mẫu đều để so sánh và tương thích thư viện cũ. Thêm `hybrid`: quét chuyển cảnh bằng FFmpeg `scale=160:-2,scdet=threshold=10`, vẫn giữ mọi mốc đều và thêm một frame cách đầu cảnh tối đa 0,2 giây khi mốc đều chưa phủ nửa giây đầu. Đây là offset cố định, chưa phải phép đo frame đã ổn định. Đọc mọi frame để dò cut; không dùng một probe mỗi vài giây rồi coi các cảnh giữa probe là đã được kiểm tra.
- Cache mốc chuyển cảnh độc lập với fps, có fingerprint/version và ghi file nguyên tử; dựng lại kế hoạch từ cache và fps hiện tại. Pause/cancel khi quét phải dừng tiến trình con. Checkpoint giữ vị trí frame kế tiếp dưới dạng frame/native_fps; resume không thêm trùng. Tiến độ quét và encoding tách nhau.
- Không gộp đoạn qua ranh giới chuyển cảnh; text smoothing của index hybrid dùng thời gian thật thay vì số lượng frame. Tìm bằng text của chỉ mục uniform giữ luồng cũ.
- Thêm chế độ ảnh `detail`: EG2 chọn ứng viên, SIFT + ratio/mutual matching + RANSAC kiểm tra hình học và màu ảnh. Chỉ phù hợp tìm lại screenshot/chi tiết đủ texture, không coi đây là bộ nhận dạng mọi vật thể đổi góc. Không âm thầm dùng ngưỡng cosine từ DAVIS cho video người dùng.
- Bước đối chiếu có ngân sách ứng viên hữu hạn và thông báo rõ ảnh thiếu chi tiết / không đủ bằng chứng / file không đọc được. Giữ chế độ tìm tương tự và tìm ngôn ngữ tự nhiên. Không gọi điểm similarity hay số keypoint là xác suất đúng.

## Kiểm chứng

1. Video tổng hợp có cảnh rất ngắn nằm giữa các mốc đều: hybrid phải lập chỉ mục được cảnh đó. Kiểm tra pause/resume/cancel, cache và timestamp; có test đoạn không bắc qua cut.
2. Ảnh có cùng bố cục/crop/biến đổi hình học phải đối chiếu được; ảnh khác, ảnh trơn hoặc chỉ trùng một góc nhỏ không được tự nhận là chắc chắn khớp.
3. Bộ DAVIS đã xem kết quả được dùng làm **regression**, không gọi lại là test mù. Lưu toàn bộ lượt đúng/sai và tỷ lệ từ chối nhầm. Dùng dev để quyết định tham số; không sửa tham số theo nhóm test.
4. Quét và lập chỉ mục toàn bộ video gameplay trên thư viện riêng; giữ bản cũ để đối chứng. Chọn timestamp truy vấn trước khi chạy tìm kiếm, giữ query ngoài lưới index; đo tìm lại mốc nguồn và xem trực tiếp ca sai. Nếu không có nhãn đầy đủ 2h11m, không gọi đó là recall toàn bộ đối tượng.
5. Kiểm tra text, image mode, settings và silent playback qua API/Playwright; frontend build giữ các lab hiện có. Báo cáo số thực chạy và giới hạn; không tuyên bố tăng tốc từ một lần chạy.
