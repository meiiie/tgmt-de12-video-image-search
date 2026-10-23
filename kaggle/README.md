# Kaggle kernel (CHƯA push – chờ Darren duyệt)
- `kernel-metadata.json`: is_private=true, enable_gpu=true, enable_internet=true, machine_shape=NvidiaTeslaP100 (đổi sang `NvidiaTeslaT4` cho 2×T4 – giá trị theo Kaggle API, chưa xác minh với CLI hiện tại).
- Secrets cần tạo trên Kaggle: `HF_TOKEN`, `GH_TOKEN` (repo private). Đọc qua `kaggle_secrets.UserSecretsClient`, không có token trong code.
- Push (khi được duyệt): `kaggle kernels push -p kaggle/`
