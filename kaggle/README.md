# Kaggle kernel (CHƯA push – chờ Darren duyệt)
- Benchmark 70 video được **tạo ngay trong kernel** (tải DAVIS 2017 ~833 MB trong kernel, chạy prepare_davis + add_distractors); không cần dữ liệu từ box.
- `kernel-metadata.json`: is_private=true, enable_gpu=true, enable_internet=true, machine_shape=NvidiaTeslaP100 (hoặc `NvidiaTeslaT4` cho 2×T4 – giá trị chưa xác minh với Kaggle CLI hiện tại).
- **Secrets**: `HF_TOKEN` (đã tạo), `GH_TOKEN` (cần tạo – repo GitHub private). kernel-metadata.json **không có trường gắn secret**; theo hiểu biết của tôi (chưa xác minh) Kaggle API/CLI không gắn secret được → sau lần push đầu phải mở notebook trên web: Add-ons → Secrets → bật HF_TOKEN và GH_TOKEN cho notebook này, rồi chạy lại. Code chỉ đọc qua `kaggle_secrets.UserSecretsClient`.
- Thay thế không cần GH_TOKEN: upload code repo thành Kaggle Dataset private và thêm vào `dataset_sources`.
- Push (khi được duyệt): `kaggle kernels push -p kaggle/`
