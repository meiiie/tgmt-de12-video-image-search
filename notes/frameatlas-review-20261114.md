# FrameAtlas theo góp ý sau trình bày

Mục tiêu được xác nhận ngày 14/11/2026. Cập nhật sản phẩm trong desktop, có số khung qua ngưỡng theo video, phép đo lập chỉ mục và truy vấn trên mười tệp, và truy vấn ảnh được lấy ngoài các video. Chỉnh báo cáo từ bản DOCX người dùng gửi, giữ bìa, kiểu chữ, lề và ba sơ đồ.

1. Đọc và chạy cấu hình hiện có, lưu kết quả trước thay đổi. Đo đọc khung độc lập và đường tìm kiếm đủ từ ảnh tới JSON.
2. Tăng tốc chỗ có bằng chứng, ghi thời gian các công đoạn. Thống kê số khung trước Top-K và riêng số khung đối chiếu, không dùng số khoảnh khắc thay cho số ảnh.
3. Bổ sung bảy đoạn 2–3 phút từ bốn phim công khai vào ba video có sẵn. Đây là mười tệp, không phải mười bản ghi độc lập. Ghi nguồn và thời gian cắt. Không gọi các đoạn là bộ chuẩn có nhãn.
4. Chạy kiểm tra backend, frontend và luồng EG2 thật. Chạy ít nhất năm cặp đo A/B cho tối ưu trước khi kết luận tốc độ.
5. Cập nhật báo cáo theo cấu hình thực, số đo hiện tại và ảnh sản phẩm. Kết xuất và đối chiếu mục lục trước bàn giao.

Luồng đọc hiện tại xử lý từng video trên một worker. Mỗi lô đọc, suy luận và lưu theo thứ tự. Luồng tìm giữ khóa một yêu cầu, nạp ma trận vector khi chỉ mục thay đổi, tính matrix @ q trên toàn phạm vi rồi gộp đoạn. Nhánh chi tiết kiểm tra tuần tự tối đa 48 khung. Dùng thư viện tính toán native có thể đa luồng nhưng không phải mở đồng thời mười video trong mỗi lượt tìm.

Không dùng subagent theo AGENTS.md. Không mở Gradio. Runtimes, trọng số, video, ảnh truy vấn, đầu ra và token giữ ngoài Git.
