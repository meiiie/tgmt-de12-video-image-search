# Baseline local ngày 01/11/2026

Múi giờ Asia/Saigon. Source gốc `be13268a60a72d812dfd8105350fe8fc6ddec3dd`. Nhánh làm việc `chore/onboarding-baseline`.

## Phạm vi

Đã clone repo, đọc các chat liên quan, đối chiếu Neko Aurora và hai tài liệu workflow, lập bản đồ code, và tự tái hiện lỗi temporal. Quy tắc người dùng yêu cầu được lưu trong `AGENTS.md` của workspace và repo: chỉ agent chính thực hiện, không dùng subagent.

Các file mới phục vụ khảo sát và kiểm chứng. Source thuật toán `vsearch/`, app, metric và mặc định backbone chưa thay đổi. Không commit, push hoặc deploy trong bước khảo sát này.

## Môi trường

- Windows build 26300, Intel Core i7-11800H, 8 lõi/16 luồng, RAM khoảng 15.7 GiB.
- Python tìm thấy ban đầu là 3.10.9. Torch global 2.9.1+cpu báo CUDA không khả dụng.
- Venv riêng tại `.venv`, không dùng system site packages. Dependency được cài theo `requirements.txt` với PyTorch CPU index.
- Chưa tìm thấy `ffmpeg` trong PATH. Smoke video dùng OpenCV, không cần CLI ffmpeg.
- Chưa có `de_bai.pdf` trong checkout. `research.md` ghi môi trường đề là Python 3.12; lần chạy Python 3.10 này chỉ kiểm tra khả năng chạy local, không xác nhận tuân thủ đầy đủ môi trường đề.

## Lệnh setup

Chạy PowerShell tại root repo. Gọi trực tiếp interpreter của venv, không cần thay ExecutionPolicy.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip check
```

Setup đã hoàn tất, exit 0. `pip check` trả `No broken requirements found.` Log cài local ở `.venv/install.log`, được Git bỏ qua.

| Dependency | Phiên bản đã cài |
|---|---|
| torch | 2.14.1+cpu |
| torchvision | 0.29.2+cpu |
| transformers | 5.20.2 |
| sentence-transformers | 6.2.0 |
| faiss-cpu | 1.15.1 |
| opencv-python-headless | 5.0.0.93 |
| numpy | 2.2.6 |
| gradio | 6.31.0 |

Snapshot đầy đủ ở `outputs/onboarding/requirements-resolved.txt`; phiên bản chính ở `outputs/onboarding/environment.json`. Đây là snapshot local, chưa thay thế `requirements.txt` của dự án.

## Kiểm tra logic temporal

Đã chạy bằng Python global có sẵn numpy và torch:

```powershell
py -3.10 scripts/audit_temporal.py --out outputs/onboarding/temporal-baseline.json
```

Kết quả: exit 1, cả 3 bất biến đều FAIL. Đây là các lỗi baseline đã tái hiện, không phải lỗi cài đặt script.

| Bất biến | Quan sát |
|---|---|
| Top-1 không phụ thuộc thứ tự video | Thứ tự thuận chọn `4.mp4` điểm 0.5; đảo thứ tự chọn `6.mp4` điểm 0.99 |
| Không bỏ sự kiện tách rời | Mất peak tại 3 giây trong đường điểm `[0.9, 0.8, 0, 0.7, 0]` |
| Truy vấn ordinal trên một frame không crash | `IndexError: list index out of range` |

Output JSON ở `outputs/onboarding/temporal-baseline.json`. Thư mục outputs không vào Git. [Bản phân tích](../docs/logic-review.md) ghi nguyên nhân và vị trí code.

Đã chạy lại cùng audit bằng `.venv/Scripts/python.exe`; cả 3 lỗi vẫn tái hiện, exit 1. Kết quả ở `outputs/onboarding/temporal-venv.json`. Lỗi không phụ thuộc riêng vào môi trường Python global.

## Smoke bằng model thật

Script tạo hai video tổng hợp dài 2 giây, lấy mẫu 1 fps, dùng model thật để lập index rồi truy vấn ảnh. Query có cùng hình dạng với video đích để kiểm tra đường đi dữ liệu. Đây không phải dữ liệu kiểm định độc lập hay phép đo độ chính xác.

```powershell
.\.venv\Scripts\python.exe scripts/smoke_local.py
```

Mặc định dùng DINOv2-small công khai. Trong phiên này đã tải 3 file `config.json`, `preprocessor_config.json`, `model.safetensors` từ [facebook/dinov2-small](https://huggingface.co/facebook/dinov2-small/tree/ed25f3a31f01632728cabb09d1542f84ab7b0056), revision `ed25f3a31f01632728cabb09d1542f84ab7b0056`, vào `data/models/dinov2-small`. Model safetensors có 88,249,960 byte. Có thể chạy offline với thư mục đó:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_local.py --model "D:/BaiThayTuan/tgmt-de12-video-image-search/data/models/dinov2-small"
```

Mỗi lần chạy tạo `data/smoke-*` riêng, giữ video, query, index và `report.json`. Script in câu lệnh chạy Gradio với index vừa tạo. DINOv2 chỉ kiểm tra truy vấn ảnh; không dùng nó để tuyên bố tìm chữ hoạt động.

Đã chạy thành công, exit 0. Lần chạy này tạo `data/smoke-9lxwfmyv`, gồm 2 video, 4 frame, 4 vector. Top-1 là `red_square.mp4`, đúng fixture truy vấn. Báo cáo ở `data/smoke-9lxwfmyv/report.json`; log ở `outputs/onboarding/smoke.log`. Không suy ra độ chính xác trên dữ liệu thật từ kết quả này.

## Demo Gradio đã kiểm tra

```powershell
.\.venv\Scripts\python.exe app.py --index data/smoke-9lxwfmyv/index --videos data/smoke-9lxwfmyv/videos --port 7860
```

- Endpoint `http://127.0.0.1:7860/config` trả HTTP 200, Gradio 6.31.0.
- Đã gọi callback tìm ảnh qua `gradio_client`, `fn_index=0`, ảnh `data/smoke-9lxwfmyv/query.png`, mode `frame`, top-K 2.
- Gallery có 2 kết quả. Dòng đầu của bảng là `red_square.mp4`, đúng fixture.
- Bằng chứng ở `outputs/onboarding/app-health.json` và `outputs/onboarding/app-image-query.json`.
- Demo local được giữ chạy sau phiên này. Thông tin process tại `outputs/onboarding/app-process.json`; stdout/stderr ở cùng thư mục. Không bật `--share`.

Đây là kiểm tra callback thật của app, chưa phải kiểm tra bố cục trên trình duyệt. Demo hiện dùng DINOv2 nên chỉ nghiệm thu luồng ảnh; ô tìm chữ vẫn cần backbone hỗ trợ text.

## Kiểm tra các file mới

Đã kiểm tra cú pháp Python của hai script và liên kết nội bộ trong các tài liệu mới. `git diff --check` không báo lỗi. Đã đối chiếu `git diff` để xác nhận `vsearch/`, `app.py`, requirements, evaluator và notebook vẫn đúng source baseline.

## Các mốc chưa được tái hiện

- EG2 frame-only trên DAVIS 70 video và độ chính xác trong README.
- Charades-STA, threshold nhiều miền, SAM/OWLv2 và GPU benchmark.
- Notebook Colab Run all. Notebook hiện còn placeholder clone.
- Đối chiếu rubric gốc của giảng viên.

Các hạn chế này độc lập với kiểm tra cú pháp hoặc smoke nhỏ. Số liệu cũ vẫn là kết quả được lưu trong repo, chưa phải số đo mới trên máy này.
