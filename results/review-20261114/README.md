# Số liệu phục vụ lần góp ý ngày 14/11/2026

Đây là kết quả **đã đo và lưu ngày 14/11/2026**, đưa vào kho ngày 16/11/2026. Chúng không phải số đo được chạy lại khi công bố mã. Đường dẫn máy cá nhân, lịch sử truy vấn và chữ ký chứa đường dẫn đã được bỏ; các giá trị số được giữ nguyên.

- `index-comparison.json`: năm cặp lập chỉ mục mới, tắt/bật đọc trước, cùng mẫu video, cấu hình và mô hình. Mã đo: `scripts/benchmark_review.py`.
- `device-comparison.json`: năm cặp CPU FP32 và CUDA BF16; lưu thời gian, số khung và mức đồng thuận của vector. Mã đo: `scripts/benchmark_device_review.py`.
- `index-ten-videos.json`: trạng thái và thời gian lập chỉ mục bộ mười tệp.
- `media-manifest.json`: nguồn, thời điểm cắt và thông tin các đoạn bổ sung. Mười tệp không đồng nghĩa với mười bản ghi độc lập; một số tệp là những đoạn cắt không chồng lấn của cùng phim nguồn.

Các kịch bản đo cần điều chỉnh đường dẫn, chuẩn bị lại dữ liệu và dùng chỉ mục mới trước khi chạy trên máy khác. Bộ này dùng kiểm tra tích hợp và hiệu năng; không phải bộ chuẩn có nhãn để kết luận độ chính xác chung. Xem thêm [báo cáo và thuyết trình](../../docs/submission/README.md).
