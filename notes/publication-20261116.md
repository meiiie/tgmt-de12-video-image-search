# Kiểm tra trước khi công bố FrameAtlas — 16/11/2026

Phạm vi: đưa toàn bộ phần mã FrameAtlas đang làm việc lên nhánh chính, gồm các commit desktop trước đó, phần thống kê/đo thời gian theo góp ý, kịch bản thực nghiệm và tài liệu hoàn thiện. Không thay thuật toán trong lần chuẩn bị công bố này.

Các kiểm tra chạy lại trên Windows:

- `python -m pytest desktop/tests -q`: 32 kiểm thử đạt.
- `npm run build`: TypeScript và Vite hoàn tất; có cảnh báo chú thích từ phụ thuộc Zod, không gây lỗi build.
- `FRAMEATLAS_UI_REUSE=1 npm run test:ui`: 7 kiểm thử giao diện đạt, gồm tìm ảnh/văn bản, crop, phát, lưu và xuất đoạn.
- `python scripts/audit_temporal.py`: 3 bất biến thời gian đạt.
- Luồng EG2 thật: dùng runtime CUDA hiện có, mô hình thật và bản sao SQLite riêng của thư viện 10 video / 5.480 khung; tìm bằng ảnh và bằng chữ đều trả 5 kết quả, tổng số khung theo video nhất quán. Worker lập chỉ mục không được khởi chạy trong phép thử này. Không sửa thư viện gốc; đây là kiểm tra tích hợp, không phải phép đo tốc độ hay độ chính xác.

Word và PowerPoint trong `docs/submission/` được sao nguyên byte từ bản đã kiểm tra ở lần biên tập trước. Dữ liệu số trong `results/review-20261114/` là phép đo lịch sử; đường dẫn và lịch sử cá nhân đã bỏ khi công bố.

Tệp nguồn, nội dung XML của tài liệu Office và các blob trong những commit mới đã được rà theo mẫu khóa truy cập phổ biến, khóa riêng và token phiên cục bộ. Video nguồn, trọng số, cơ sở dữ liệu, `node_modules`, runtime và đầu ra tạm nằm ngoài tập tệp công bố.
