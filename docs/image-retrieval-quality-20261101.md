# Đo bỏ sót, nhận nhầm và tiền xử lý ảnh

Ngày 01/11/2026. Phạm vi: ảnh toàn cảnh hoặc crop → video nguồn và mốc/đoạn có đối tượng. Tìm bằng ngôn ngữ tự nhiên được giữ như chức năng mở rộng. Thử nghiệm này không đổi model, ngưỡng mặc định hoặc thư viện video người dùng.

## Thiết kế phép đo

[Protocol đã khai báo trước khi chạy model](lab/image-retrieval-quality-protocol.json) dùng ảnh và instance mask từ [DAVIS 2017 trainval 480p](https://davischallenge.org/davis2017/code.html). Chọn 16 sequence có mục tiêu là động vật/đồ vật, ghép thành 4 video 24 fps tổng 37,5 giây. Thêm 12 sequence khác chỉ làm truy vấn vắng. Đây là bài thử truy hồi tự xây từ video thật, **không phải benchmark DAVIS segmentation chính thức**.

- Ảnh truy vấn tại frame 0/4/8; loại toàn bộ 12 frame đầu khỏi gallery. Nhãn thời gian lấy từ mask hiện diện ít nhất 25 pixel; khoảng có dạng `[start,end)`. Không loại truy vấn nào vì điểm model thấp.
- 27 đối tượng có mặt và 12 đối tượng vắng, mỗi đối tượng có 3 ảnh. Crop bbox gốc, hoặc thêm 15%/40% chiều rộng và cao ở mỗi phía. Thêm 3 ảnh toàn cảnh cho mỗi sequence. Tổng 435 đầu vào kể cả các biến thể, không phải 435 mẫu độc lập.
- Chia theo sequence: dev có 13 đối tượng dương/6 âm, test có 14 dương/6 âm. Ở một cấu hình crop, test gồm **42 truy vấn dương + 18 âm**. Với ảnh toàn cảnh, test gồm **24 dương + 18 âm**. Đây là split riêng của dự án, không phải train/val gốc của DAVIS.
- Không fine-tune model. EG2 đúng revision của app, CUDA BF16, 768 chiều, 140 vision tokens, không nạp audio. Dùng thư viện desktop riêng và code temporal production; không đụng thư viện gameplay live.
- Index 2 fps bằng decoder và timestamp thật của desktop; các cấu hình thưa hơn là tập con cùng lưới frame. So sánh 0,1/0,5/1/2 fps, crop 0/15/40%, và frame + 4 vùng lưới ở 1 fps. Không đo tốc độ decoder của từng mức fps.
- Chọn ngưỡng riêng cho ảnh toàn cảnh/crop và từng cấu hình, **chỉ trên dev**: tối đa 5% truy vấn vắng được trả kết quả, rồi tối đa số truy vấn dương đúng top 1; hòa thì ít nhận sai hơn, sau đó ngưỡng cao hơn. Với 18 câu âm, ngân sách 5% tương đương **0 câu âm được nhận**. Chọn cấu hình bằng F1 top 1 đã áp ngưỡng trên dev; hòa thì ưu tiên ít vector hơn. Không dùng test để chọn lại.

## Đọc số liệu đúng cách

“Đúng mốc” yêu cầu cùng video và peak nằm trong khoảng nhãn, không cộng dung sai. Recall@5 là tỷ lệ truy vấn dương có ít nhất một kết quả đúng trong 5 kết quả đầu; bỏ sót@5 là phần còn lại. Độ phủ lấy mẫu được đo trước model: có khung index trong khoảng nhãn hay không.

“Nhận truy vấn vắng” nghĩa là trả ít nhất một ứng viên cho mục tiêu không có trong gallery. Khi tắt ngưỡng, hệ thống luôn gợi ý các ứng viên gần nhất; con số này không có nghĩa app đã tuyên bố chúng là xác nhận danh tính. Sau ngưỡng, tách rõ từ chối nhầm truy vấn dương, nhận sai top 1 trên truy vấn dương và trả kết quả cho truy vấn âm.

Độ đúng đoạn được đo thêm bằng temporal IoU ≥ 0,5; một đoạn kéo dài cả video không được điểm hoàn hảo chỉ vì chạm nhãn. Event recall dùng ghép một-một để không đếm lặp cùng lần xuất hiện. Chỉ số này khác tìm trúng một khung.

Nhiều con vật trong cùng frame có khoảng hiện diện trùng nhau. Kết quả chỉ chứng minh **tìm đúng video/mốc chứa đối tượng theo nhãn**, không chứng minh model đã định vị đúng cá thể trong frame hoặc nhận diện danh tính xuyên camera. Ba ảnh của một mục tiêu và nhiều mục tiêu cùng scene có tương quan; không báo khoảng tin cậy giả định mọi truy vấn độc lập.

## Kết quả chạy thực

Lượt hoàn tất: `outputs/retrieval-quality/run-v3/`, EG2 BF16 trên RTX 3050 Ti. Không có query bị loại. Cả 3 ca đối chiếu trả cùng top 10/video/peak như `Library.search` thật, sai số điểm kiểm tra ≤ 1e-6. Tất cả vectors hữu hạn và chuẩn hóa; 77 timestamp của index 2 fps khớp lưới frame giải mã. [Summary đầy đủ](../results/image-retrieval-quality-20261101.json) và [CSV 1.407 dòng query/cấu hình](../results/image-retrieval-quality-20261101-queries.csv) giữ cả ca đúng và sai. Nhiều dòng dùng lại cùng query, không phải 1.407 mẫu độc lập.

### Tìm đối tượng, chưa đặt ngưỡng

Tất cả hàng có cùng 42 truy vấn dương trên test; các biến thể padding thay đổi crop của cùng mục tiêu.

| Cấu hình | Số vector | Có frame trong nhãn | Đúng top 1 | Trúng top 5 | Bỏ sót top 5 | Đoạn top 1 đạt IoU ≥ 0,5 |
|---|---:|---:|---:|---:|---:|---:|
| 0,1 fps, pad 15% | 5 | 3/42 | 3/42 | 3/42 | 39/42 | 3/42 |
| 0,5 fps, pad 15% | 21 | 39/42 | 36/42 | 39/42 | 3/42 | 21/42 |
| **1 fps, pad 15% — baseline** | 40 | 42/42 | 39/42 | 41/42 | 1/42 | 34/42 |
| 2 fps, pad 15% | 77 | 42/42 | 39/42 | 42/42 | 0/42 | 36/42 |
| 1 fps, crop sát bbox | 40 | 42/42 | 38/42 | 40/42 | 2/42 | 33/42 |
| 1 fps, pad 40% | 40 | 42/42 | 41/42 | 42/42 | 0/42 | 35/42 |
| 1 fps, frame + 4 vùng, pad 15% | 200 | 42/42 | 40/42 | 42/42 | 0/42 | 35/42 |

Ở mọi hàng chưa đặt ngưỡng, **18/18 truy vấn vắng đều nhận ứng viên**. Hệ thống xếp hạng gần nhất chưa có quyết định từ chối, nên không được diễn giải mọi kết quả là đã xác nhận đúng đối tượng.

**Ảnh hưởng thứ tự ghép:** cả 4 video nhân tạo đều bắt đầu bằng scene dev. Ở 0,1 fps, lưới bắt đầu tại 0 s chủ yếu rơi vào scene dev, nên con số 3/42 trên test còn chịu ảnh hưởng pha lấy mẫu. Không dùng 92,9% bỏ sót này để ước lượng lỗi trên video dài hoặc khẳng định một hệ số cải thiện tổng quát. Ở baseline 1 fps, mọi mục tiêu test đều có frame nhưng vẫn có lỗi xếp hạng; thêm frame hoặc bối cảnh có thể giúp chọn góc nhìn tốt hơn.

### Sau ngưỡng chọn trên dev

| Cấu hình | Ngưỡng dev | Đúng và được nhận /42 | Dương bị từ chối /42 | Âm vẫn được nhận /18 |
|---|---:|---:|---:|---:|
| 0,1 fps, pad 15% | 0,874831 | 3 | 39 | 0 |
| 0,5 fps, pad 15% | 0,866319 | 29 | 13 | 0 |
| 1 fps, pad 15% | 0,866319 | 29 | 13 | 0 |
| 2 fps, pad 15% | 0,866319 | 29 | 13 | 0 |
| 1 fps, crop sát bbox | 0,816167 | 32 | 10 | 3 |
| **1 fps, pad 40% — được chọn trên dev** | **0,842612** | **40** | **2** | **3** |
| 1 fps, frame + 4 vùng, pad 15% | 0,888478 | 31 | 11 | 0 |

Không có top 1 sai được nhận ở các truy vấn dương sau các ngưỡng này; lỗi còn lại nằm ở từ chối nhầm và nhận truy vấn vắng. Không vì vậy suy ra sai số bằng không trong thư viện khác.

Cấu hình pad 40% đạt 39/39 đúng và 0/18 nhận âm trên dev, nhưng trên test còn **40/42 đúng (95,2%)**, từ chối **2/42 (4,8%)**, nhận âm **3/18 (16,7%)**. Ba ảnh âm ấy thuộc **một** mục tiêu `rhino`, bị trả cảnh `elephant` với điểm 0,852–0,862, cao hơn ngưỡng. Đã xem ảnh/cảnh đối chiếu: tê giác và voi có hình dáng/màu và bối cảnh đá, chuồng khá gần. Đây là quan sát có thể giải thích sự nhầm lẫn, không phải phép chứng minh nhân quả về đặc trưng nội bộ model. Hai truy vấn dương bị từ chối thuộc cùng con cừu nhỏ `sheep-object5`; một truy vấn còn xếp lạc đà lên đầu trước ngưỡng.

Crop thêm bối cảnh có ích trong tập này nhưng cũng có nguy cơ khớp bối cảnh của đối tượng khác. Lưới vùng tăng từ 40 lên 200 vector, chỉ tăng top 1 từ 39 lên 40/42 ở pad 15%; chưa có căn cứ chọn làm mặc định. Không suy ra thời gian chạy tăng đúng 5 lần từ số vector.

Nhóm mask nhỏ hơn 5% frame có 21 truy vấn dương / 7 mục tiêu (3 scene), baseline đúng top 1 18/21; pad 40% là 20/21, lưới vùng là 19/21. Các nhóm theo diện tích có thể chứa các frame khác nhau của cùng mục tiêu quanh ngưỡng 5%, nên không cộng số target giữa các nhóm như thể chúng độc lập.

### Ảnh toàn cảnh, đoạn thời gian và ngôn ngữ tự nhiên

Ở 1 fps, ảnh toàn cảnh đúng top 1 **24/24** trước ngưỡng, nhưng chỉ **20/24** đoạn top 1 đạt IoU ≥ 0,5; trúng mốc chưa bảo đảm lấy đúng cả đoạn. Sau ngưỡng 0,901670, còn **22/24** đúng và **0/18** nhận âm.

Quy tắc chọn cấu hình trên dev lại chọn **0,5 fps** cho ảnh toàn cảnh vì hòa F1=1,0 và ít vector hơn. Kết quả test của lựa chọn đó chỉ **18/24** đúng sau ngưỡng, 6 truy vấn bị từ chối, 0/18 nhận âm. Giữ nguyên lựa chọn và công khai kết quả yếu hơn, không âm thầm đổi sang cấu hình có test đẹp hơn. Cần thêm dữ liệu/pha lấy mẫu trước khi tự động quyết định mức fps cho sản phẩm.

Tám truy vấn ngôn ngữ tự nhiên (4 ý × Việt/Anh) chạy trực tiếp qua `Library.search(text=...)` đều đúng top 1 trên index 2 fps. Đây là kiểm tra giữ chức năng và khả năng tìm các cảnh mẫu, không phải benchmark chất lượng ngôn ngữ toàn diện.

Kiểm tra phần mềm: **28 ca backend + metric tests**, **6 luồng UI**, 3 bất biến temporal đều qua. Trang review kiểm tra 28 trạng thái cấu hình/ý định/ngưỡng, bộ lọc bỏ sót/nhận âm, ảnh tải được, không lỗi console và không tràn ngang ở 920 px. Mở [lab đọc từng ca](http://127.0.0.1:1420/retrieval-quality-20261101/) khi server local còn chạy; HTML/media sinh ra nằm trong `desktop/dist/retrieval-quality-20261101/`, bị Git ignore. Không đóng gói lại portable vì lượt này không thay logic ứng dụng production.

## Tiền xử lý và hướng cải thiện

Chuẩn hóa đầu vào là điều kiện cần: đọc đúng EXIF, đổi RGB, giữ tỉ lệ và crop từ pixel nguồn. EXIF/crop đã được kiểm tra ở [lượt trước](image-search-practical-workflow.md); phép đo lần này không chứng minh lại từng biến đổi ấy.

Phải đo độ phủ lấy mẫu trước khi đổi model. Không có frame chứa mục tiêu thì embedding không thể tìm lại một chi tiết chưa được quan sát. Mức 0,1 fps hữu ích để quét sơ bộ video dài nhưng không cam kết bắt được đoạn ngắn. Bước thiết kế tiếp theo là lấy frame theo chuyển cảnh kèm lưới thời gian dự phòng, rồi đo lại cùng nhãn; chưa triển khai trong lượt này.

Một ứng viên để thử là [ContentDetector/AdaptiveDetector của PySceneDetect](https://www.scenedetect.com/docs/latest/api/detectors.html): chúng tìm thay đổi giữa các frame, AdaptiveDetector dùng ngưỡng theo cửa sổ lân cận để giảm ảnh hưởng chuyển động camera. Đây là tín hiệu chuyển cảnh, không bảo đảm phát hiện một vật nhỏ vừa đi vào cảnh; vì vậy vẫn cần lưới thời gian dự phòng. Cũng chưa bật lọc trùng trước embedding: phải chứng minh việc bỏ frame không làm mất lần xuất hiện ngắn.

Crop hẹp, crop có bối cảnh và chỉ mục vùng cần đo riêng. Lưới vùng không phải detector, có thể cắt đôi đối tượng và tăng điểm của những vật cùng loại. Không triển khai chỉ vì vài ví dụ đẹp. Không mặc định làm nét, khử nhiễu hoặc super-resolution bằng AI: chúng có thể làm thay đổi chi tiết cần đối chiếu; chưa có phép đo cho các biến đổi đó ở đây.

Điểm cosine không phải xác suất đúng. Ngưỡng thỏa dev không bảo đảm cùng tỷ lệ nhận nhầm ở video khác. Chưa đưa ngưỡng của pilot vào app; trước khi dùng thật cần tập có nhãn đại diện video đích, truy vấn vắng khó và cách xử lý “chưa đủ bằng chứng”. Tìm ngôn ngữ tự nhiên tiếp tục dùng luồng hiện tại, không bị áp ngưỡng crop.

## Chạy lại và xem từng trường hợp

Từ root repository, tải archive theo URL trong protocol vào `data/davis-quality/trainval-480p.zip`. Chạy với output mới để giữ bằng chứng cũ. Runtime CUDA có model/dependencies như báo cáo; bước chuẩn bị và metric tests chạy được bằng `.venv` CPU.

```powershell
.venv/Scripts/python.exe scripts/prepare_retrieval_quality.py --archive data/davis-quality/trainval-480p.zip --protocol docs/lab/image-retrieval-quality-protocol.json --output data/davis-quality/pilot-new
$env:PYTHONUTF8='1'
$env:HF_HUB_OFFLINE='1'
outputs/releases/FrameAtlas-CUDA/runtime/python.exe scripts/evaluate_retrieval_quality.py --dataset data/davis-quality/pilot-new --model data/models/embeddinggemma-2 --output outputs/retrieval-quality/new-run
.venv/Scripts/python.exe -m pytest desktop/tests scripts/test_retrieval_quality_metrics.py -q
```

Khi đã có `embedding-run.json` và `embeddings.npz`, thêm `--score-only` để tính lại báo cáo trên cùng vectors; manifest hash phải khớp. `build_retrieval_quality_review.py` nhận `--report`, `--dataset`, `--output`, `--csv` để tạo trang đọc kết quả và CSV đầy đủ. Trang review chỉ đọc SQLite qua kết nối `mode=ro`, không khởi tạo worker hoặc thay thư viện.

## Giới hạn và provenance

- Chỉ 16 scene trong gallery, clip ngắn ghép nhân tạo; không suy rộng tỷ lệ này sang video gameplay 2 giờ 11 phút hoặc kho video lớn. Các query frame bị giữ ngoài index nhưng vẫn rất gần cảnh gallery. Chưa có thử nghiệm đổi góc/quần áo/ánh sáng xuyên video với nhãn độc lập.
- Không biết model pretraining có chứa DAVIS hay không. Không gọi đây là dữ liệu hoàn toàn chưa từng thấy.
- Archive hash, protocol hash, code hash, model-file hash, versions và dtype được lưu trong báo cáo. Media, database, vectors và full report ở `data/`/`outputs/` bị Git ignore. Bản summary và CSV không chứa token hoặc đường dẫn media cá nhân.
- Archive README ghi CC BY ở Credits nhưng CC BY-NC ở Terms of Use; giữ cả README/SOURCES nguyên bản trong `provenance/` và chỉ dùng media nghiên cứu local. Không đóng gói chúng vào sản phẩm. Xem [third-party provenance](../desktop/THIRD_PARTY.md).
- Lượt đầu dùng query batch 4 bị chặn bởi kiểm tra parity: một số điểm sát nhau đổi vị trí cuối top 10. Chẩn đoán cùng dữ liệu cho thấy batch 1 khớp luồng app. Không dùng lượt thất bại để chọn tham số/threshold. Lượt kế tiếp dừng ở bước metadata do OpenCV được cài dưới distribution headless; sửa cách đọc phiên bản runtime và chạy lại đầy đủ. Các lần thất bại không được tính là kết quả benchmark thành công.
