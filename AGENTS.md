# Hướng dẫn cho agent

## Quy tắc bắt buộc của người dùng

- Chỉ agent chính được tự thực hiện công việc. Tuyệt đối không dùng subagent hoặc giao việc cho agent phụ.
- Không tạo hoặc sử dụng chat/thread khác để làm thay. Có thể đọc lịch sử liên quan khi người dùng yêu cầu.
- Nếu skill hay playbook yêu cầu phân công agent, bỏ bước phân công và tự làm phần việc đó.
- Quy tắc này chỉ được thay đổi khi người dùng yêu cầu rõ ràng.
- Mở và kiểm thử UI trong tab bên phải của Codex; chạy công việc còn lại trong nền. Không giành chuột/bàn phím hoặc mở cửa sổ native nổi lên làm gián đoạn việc học của người dùng.

## Cách làm việc

- Đề tài chính người dùng xác nhận: xây dựng hệ thống tìm kiếm hình ảnh trong video. Ưu tiên luồng ảnh toàn cảnh/crop đối tượng → video nguồn và các đoạn xuất hiện; các hướng khác là mở rộng.
- Giữ chức năng tìm bằng ngôn ngữ tự nhiên như một hướng mở rộng. Cải thiện tìm bằng ảnh không được xóa hoặc làm hỏng luồng tìm bằng văn bản.
- Ưu tiên độ chính xác trước. Tách kiểm thử đầu vào/giao diện khỏi benchmark truy hồi; không gọi điểm cosine là xác suất đúng hoặc lấy một ca khớp làm độ chính xác chung.
- Dùng `karpathy-guidelines` khi đọc, sửa, debug hoặc review code.
- Đọc code và tái hiện baseline trước khi thay logic. Chỉ sửa trong phạm vi yêu cầu.
- Phân biệt số liệu đã lưu trong repo với kết quả chạy lại trong phiên hiện tại. Không tuyên bố đạt độ chính xác chỉ dựa vào smoke test.
- Không ghi token, dữ liệu riêng tư, video, model weights hoặc môi trường ảo vào Git.

## Điểm bắt đầu

- `desktop/README.md`: chạy và đóng gói ứng dụng Windows; `desktop/backend/` giữ thư viện, worker và EG2; `desktop/src/` là UI; `desktop/src-tauri/` quản lý tiến trình và hộp thoại native.
- Desktop cần kiểm tra backend bằng pytest, UI bằng Playwright và ít nhất một luồng EG2 thật. Không đánh đồng encoder fixture với chất lượng tìm kiếm thực tế.
- EG2 chỉ dùng FP32 hoặc BF16; không dùng FP16. Đổi preprocessing/model phải đổi chữ ký và xây lại chỉ mục.

- `app.py`: giao diện Gradio.
- `vsearch/core.py`: lấy mẫu khung, embedding, FAISS và tìm kiếm ảnh.
- `vsearch/text.py`: tìm kiếm văn bản và gộp thời gian.
- `scripts/build_index.py`, `scripts/query.py`, `scripts/evaluate.py`: CLI lập chỉ mục, truy vấn và đánh giá.
- `README.md`, `results/`, `notes/`: hướng dẫn và bằng chứng thí nghiệm đã lưu.
- Khi phân tích hoặc cải thiện pipeline, xem `docs/logic-review.md`. Quy trình và nguồn tham khảo ở `docs/working-method.md`.
- `python scripts/audit_temporal.py`: kiểm tra các lỗi temporal đã ghi nhận; exit 1 khi bất biến còn vi phạm.
- `python scripts/smoke_local.py`: kiểm tra tích hợp bằng video tổng hợp và model thật; có thể tải model, không phải benchmark độ chính xác.
