# Báo cáo và thuyết trình FrameAtlas

Các tệp hoàn thiện của đề tài 12, cập nhật ngày 14/11/2026:

- [Báo cáo Word](Bao_cao_FrameAtlas.docx): 45 trang nội dung và tài liệu tham khảo; 7 trang đầu gồm bìa và các danh mục. Có sơ đồ và ảnh chụp giao diện sản phẩm.
- [PowerPoint về EG2 và cách xây dựng hệ thống](Thuyet_trinh_FrameAtlas_EG2.pptx): 25 slide chính, khoảng 15 phút, và 5 slide phụ lục. Phần EG2 ở slide 8–16 giải thích mô hình, cách tạo vector, căn cứ lựa chọn và mã tích hợp. Năm video minh họa được nhúng trong tệp.
- [Lời thuyết trình](Loi_thuyet_trinh_EG2.md): nội dung để tập nói, cũng có trong phần Notes của PowerPoint.

Chọn **View raw / Download raw file** trên GitHub để tải Word hoặc PowerPoint. Dùng PowerPoint trên máy tính để trình chiếu các video và hiệu ứng. Các tệp giữ nguyên từ bản đã kiểm tra trong thư mục làm việc, không tạo lại khi đưa lên GitHub.

## Mã và dữ liệu dùng cho sản phẩm

- [Hướng dẫn chạy FrameAtlas](../../HUONG_DAN_CHAY.txt).
- [Cài đặt, phát triển và đóng gói Windows](../../desktop/README.md).
- `desktop/backend/`: mã hóa bằng EG2, lập chỉ mục, tìm kiếm và đối chiếu chi tiết.
- `desktop/src/`: giao diện sản phẩm; `desktop/src-tauri/`: vỏ ứng dụng Windows.
- `scripts/benchmark_review.py`, `scripts/benchmark_device_review.py`, `scripts/review_app.py`: các phép đo và thao tác kiểm chứng đã dùng cho đợt góp ý ngày 14/11/2026. Đây là kịch bản thực nghiệm trên máy làm dự án, có đường dẫn dữ liệu cục bộ cần điều chỉnh khi tái lập.
- `results/` và `docs/`: các số liệu và ghi chép nghiên cứu đã lưu. Không đánh đồng các bộ thử lịch sử với ca road1 trong bài trình bày.

Video gốc, trọng số mô hình, cơ sở dữ liệu cá nhân và môi trường chạy không nằm trong Git. Thêm video của mình qua ứng dụng; tải mô hình và dựng môi trường theo hướng dẫn desktop. Một số phim mẫu được chuẩn bị bằng `scripts/prepare_review_media.py`; cần xem nguồn và điều chỉnh thư mục đích trước khi chạy.
