# Tìm pain point: chọn cảnh từ video dài, bóng đá và creator

Ngày: 01/11/2026. Quyết định ưu tiên: **thử nghiệm trợ lý tạo danh sách cảnh cần duyệt cho editor video dài**, trước hết với video game đã có trên máy. Hướng camera giao thông trong tài liệu trước vẫn là phương án nghiên cứu; chưa tiếp tục đầu tư detector/tracker khi đang xác định người dùng đích.

## Công việc thực sự cần giải quyết

Sau một buổi quay/stream, editor cần biến nhiều giờ video thành một danh sách ngắn các đoạn có thể dựng. Công việc gồm nhớ/tìm thời điểm, xem đủ ngữ cảnh, tránh chọn nhiều đoạn lặp, ghi chú và bàn giao. Cắt MP4 chỉ là bước cuối.

Mason Lindblad mô tả trực tiếp việc dựng livestream cho một creator: không có shot list, phải tìm cảnh trong bản ghi dài, gom các lựa chọn rồi xây câu chuyện. Marker do streamer hoặc người xem tạo giúp giảm lượt rà đầu tiên nhưng phụ thuộc người ghi nhớ. Đây là trải nghiệm một editor, bài năm 2021, không phải khảo sát thị trường. [Bài viết của editor](https://filtergrade.com/how-to-edit-livestreams-youtube-highlight/)

Twitch giải thích Stream Markers xuất phát từ việc streamer/editor phải tự ghi timestamp hoặc nhớ khoảnh khắc để dựng lại. Tài liệu này củng cố sự tồn tại của công việc, không chứng minh AI sẽ làm tốt hơn marker. [Twitch announcement](https://discuss.dev.twitch.com/t/introducing-the-stream-markers-api/17571)

**Giả thuyết sản phẩm:** editor hoặc creator nhỏ làm video dài thường xuyên, có file local và ít marker, sẽ có lợi từ một lượt máy rà trước, trả các ứng viên có thể kiểm tra nhanh. Chưa phỏng vấn người dùng, chưa xác nhận khả năng trả tiền, chưa đo tiết kiệm thời gian thực tế.

Đầu ra mong muốn: 15–30 ứng viên kèm thời gian nguồn, lý do được đề xuất, đủ ngữ cảnh, giữ/bỏ/ghi chú và xuất danh sách để dựng. Số lượng này là cấu hình thử nghiệm, không có nghĩa mọi video đều chứa đủ số đoạn hay.

## Ba nhu cầu dễ bị trộn lẫn

| Người dùng | Yêu cầu cụ thể | Thế nào là kết quả đúng? |
|---|---|---|
| Editor livestream/game | Tìm các đoạn phản ứng thú vị, câu chuyện ngắn, tiếng cười, tình huống bất ngờ | Editor giữ lại đoạn và thấy đủ phần dẫn tới phản ứng/kết quả |
| Người làm nội dung bóng đá | Lấy bàn thắng, pha cứu thua, cơ hội nguy hiểm để dựng bản tổng hợp | Đúng sự kiện, đủ diễn biến, không lặp replay cùng một pha |
| HLV/analyst | Tìm các lần mất bóng ở một khu vực, pressing thất bại hoặc hoạt động của một cầu thủ | Đúng tiêu chí chiến thuật, đúng đội/cầu thủ và diễn biến |

Một pha bóng không có tiếng hò reo vẫn có thể quan trọng với HLV. Một đoạn có nhiều tiếng cười vẫn có thể vô nghĩa với người chưa xem câu chuyện trước đó. Vì vậy, cần biết người xem và mục tiêu bản dựng trước khi xếp hạng.

## Nếu là một trận bóng đá

Tình huống sản phẩm giả định: người phụ trách truyền thông của đội có bản ghi trận đấu và muốn làm video tổng hợp 60–90 giây. Ứng dụng đề xuất các pha ghi bàn/cơ hội, mở cả quá trình dẫn tới pha bóng, cho chọn góc quay hoặc replay, rồi xuất các đoạn đã giữ. Điểm khó nằm ở tìm đúng thời điểm và gộp các replay của cùng một sự kiện.

[SoccerNet Action Spotting](https://www.soccer-net.org/tasks/action-spotting) định nghĩa bài toán tìm thời điểm của 17 loại hành động trong video truyền hình dài. Nhãn là thời điểm hành động, không phải biên bắt đầu/kết thúc một clip dựng hoàn chỉnh. Điều này cho một phép đo khách quan hơn câu hỏi “pha nào hay nhất”.

Veo đã cung cấp reel từ các sự kiện như bàn thắng và cú sút trúng đích. Tài liệu sản phẩm cũng mô tả những giới hạn của reel. Dùng nguồn này để hiểu quy trình cạnh tranh; không lấy tuyên bố marketing làm kết quả chất lượng của FrameAtlas. [Veo highlight reel](https://support.veo.com/hc/en-us/articles/38958611618705-How-to-download-a-highlight-reel-from-your-recording)

Với HLV, việc gán nhãn theo triết lý đội và yêu cầu chiến thuật vẫn là công việc riêng. Hudl mô tả bổ sung tag sau trận bên cạnh dữ liệu sự kiện tiêu chuẩn. [Hudl post-match workflow](https://www.hudl.com/blog/high-performance-workflows-post-match-analysis-and-review)

**Chọn phạm vi nếu triển khai bóng đá:** tìm bàn thắng/cơ hội và hỗ trợ làm bản chọn cảnh trước. EG2 hỗ trợ truy vấn hình ảnh, tiếng khán giả/bình luận và tìm cảnh tương tự; event spotting theo thời gian, đọc bảng tỉ số và gộp replay là các phần bổ sung cần đo. Chưa có cơ sở để gán nhiệm vụ hiểu pressing, định danh cầu thủ hoặc phân xử lỗi cho EG2 đơn lẻ.

Video truyền hình có cận cảnh, replay và âm thanh bình luận khác rất xa camera góc rộng sân phong trào. Phải đánh giá hai miền riêng. [SoccerNet data](https://www.soccer-net.org/data) có dữ liệu/nhãn, nhưng một số video yêu cầu tài khoản và chấp thuận NDA; lượt này không tự chấp thuận thay người dùng và chưa chạy thử bóng đá.

## EG2 đáp ứng được đến đâu?

EG2 là model embedding đa phương thức: có thể biểu diễn chữ, ảnh, video và audio để tìm nội dung tương đồng. Encoder audio có thể nạp riêng với phần chữ. Đầu ra là vector, không phải lời giải thích hoặc bản dựng. [Google model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2), [hướng dẫn đa phương thức](https://ai.google.dev/gemma/docs/embeddinggemma/multimodal-embeddinggemma-with-sentence-transformers)

| Việc cần làm | Vai trò phù hợp của EG2 | Cần bổ sung/kiểm chứng |
|---|---|---|
| Tìm cảnh ăn mừng, màn hình bỏ phiếu, đồ vật trong ảnh | Tìm ảnh/cảnh gần nghĩa | Đánh giá đúng miền; crop/chuỗi khung khi cần |
| Tìm tiếng cười, hò reo, phản ứng mạnh | Tìm đoạn âm thanh gần mô tả | Phân biệt cười/ho/nhạc/lời nói, âm thanh trộn |
| Tìm lại câu chuyện hoặc câu nói | Tìm trong transcript theo nghĩa | ASR có timestamp và tìm từ khóa chính xác |
| Xác định lúc bóng vào lưới | Một tín hiệu đề xuất ứng viên | Temporal event spotting và kiểm tra chuỗi diễn biến |
| Chọn đoạn hài nhất | Hỗ trợ thu hẹp ứng viên | Ngữ cảnh câu chuyện, đối tượng khán giả, lựa chọn của editor |
| Dự đoán viral/triệu view | Chưa có bằng chứng đủ | Phân phối, kênh, cách dựng và khán giả là các biến khác |

App trước lượt này dùng `audio_config=None` và các ảnh lấy mẫu; chưa nghe tiếng cười. Đó là giới hạn triển khai hiện tại, không phải EG2 không hỗ trợ audio. Lượt lấy mẫu hình ảnh một ảnh mỗi 10 giây cũng có thể bỏ qua phản ứng ngắn.

QVHighlights tách nhãn khoảng liên quan tới truy vấn và điểm nổi bật do nhiều người đánh giá. Đây là cơ sở để tách “đúng thứ đang tìm” khỏi “đáng chọn làm highlight”; bộ này không xác nhận khả năng nhận biết hài hước của EG2. [QVHighlights annotation format](https://github.com/jayleicn/moment_detr/blob/main/data/README.md)

## Dự án hiện có và khoảng cần kiểm chứng

- [ClipsAI](https://www.clipsai.com/) tập trung nội dung có lời nói/câu chuyện. [ClipFinder](https://www.clipsai.com/references/clip) chia transcript theo chuyển chủ đề bằng TextTiling. Điều này giúp hiểu cách tạo đoạn mạch lạc, chưa chứng minh chọn được joke hay hoặc pha bóng quan trọng.
- [Adobe Text-Based Editing](https://helpx.adobe.com/premiere/desktop/edit-projects/edit-video-using-text-based-editing/overview-of-text-based-editing.html) đã nối transcript với cắt dựng. Chỉ bổ sung transcript vào app sẽ khó tạo khác biệt đủ mạnh.
- Marker của streamer, clip người xem đã chọn và sự kiện có sẵn là baseline quan trọng. Khi có các tín hiệu tốt này, nên nhập chúng vào danh sách duyệt thay vì cố thay bằng AI.

Lợi thế giả thuyết của FrameAtlas: Windows desktop, dữ liệu local, tìm đồng thời qua hình/âm thanh/lời nói, rồi tập trung vào duyệt và bàn giao. Chưa có bằng chứng vượt các công cụ trên về chất lượng hay chi phí. Không xây một NLE đầy đủ ở giai đoạn tìm pain point.

## Thử nghiệm đã thực hiện

### A. Audio có nhãn để kiểm tra khả năng cơ bản

`scripts/probe_highlight_audio.py` chọn trước toàn bộ fold 1 của bốn nhóm ESC-50: laughing, clapping, crying_baby, coughing. Tổng 32 file, 8 file mỗi nhóm. Dataset được pin commit `33c8ce9eb2cf0b1c2f8bcf322eb349b6be34dbb6`; lưu license/attribution bên cạnh file tải trong thư mục bị Git bỏ qua.

EG2 local, chỉ nạp text+audio, CUDA BF16, 768 chiều, chuẩn hóa lại FP32, query dùng `SearchQuery`. Audio được FFmpeg giải mã mono 16 kHz; không gửi nội dung lên dịch vụ ngoài. [ESC-50 license](https://github.com/karolpiczak/ESC-50/blob/master/LICENSE) là CC BY-NC cho tập tổng; sử dụng ở đây là thí nghiệm nghiên cứu, không đưa audio này vào bản phát hành.

Kết quả đã chạy:

- Khi xếp 32 file theo truy vấn tiếng cười tiếng Anh và tiếng Việt, cả hai đều xếp 8 file laughing lên đầu: AP = 1,0 và Precision@5 = 1,0 trong tập này.
- Khi chọn một trong bốn mô tả âm thanh, đúng 25/32 file: 6 mẫu ho bị chọn thành cười, 1 mẫu ho thành tiếng em bé khóc. Điểm số giữa những mô tả khác nhau không được hiệu chuẩn như xác suất; không đánh đồng phép phân loại đóng này với tìm kiếm.
- Tập nhỏ, một số take cùng bản ghi, thiếu lời nói/nhạc/game và không chứng minh dữ liệu chưa từng có trong huấn luyện EG2. **Không gọi đây là độ chính xác phát hiện tiếng cười trên stream hoặc khả năng chọn clip hài.**

Bằng chứng: `outputs/highlight-lab/audio/control-report.json`; dữ liệu nguồn và attribution trong `outputs/highlight-lab/audio/esc50/`.

### B. Ứng viên trên video người dùng

Pipeline chia âm thanh thành cửa sổ 10 giây, dùng các truy vấn khai báo trước: tiếng cười EN/VI, hò reo, tranh luận, âm nhạc và câu trừu tượng “khoảnh khắc hài hước nhất”. Cửa sổ liền nhau không overlap; đây là baseline đơn giản, có thể cắt ngang phản ứng hoặc câu nói.

Mỗi truy vấn giữ ứng viên cách nhau ít nhất 30 giây. Khoảng xem lại mở rộng 15 giây trước và 15 giây sau cửa sổ âm thanh; biên này là ngữ cảnh cố định, chưa được chọn theo câu chuyện. Không gắn nhãn “hay” cho kết quả tự sinh.

`scripts/build_highlight_review.py` tạo lab local có video thật, lý do được đề xuất, giữ/bỏ/cần ngữ cảnh, ghi chú và xuất JSON/CSV. Âm thanh tắt mặc định; người dùng chủ động bật khi thuận tiện. Đánh giá lưu localStorage theo fingerprint nguồn. Các clip dùng bản xem 960px/30fps, file nguồn giữ nguyên.

Kết quả đầy đủ và các số đo thực được ghi ở phần bằng chứng chạy cuối tài liệu. Không có human ground truth về đoạn nào thật sự hài hoặc đáng đăng; chưa thể tính precision highlight, recall hay tiết kiệm thời gian editor.

## Đơn vị sản phẩm tiếp theo

Làm một luồng hoàn chỉnh: chọn video → nhập mục tiêu bản dựng → xem danh sách ứng viên → nghe/xem ngữ cảnh → điều chỉnh biên đoạn → giữ/bỏ → xuất các lựa chọn và timestamp nguồn.

Thứ tự triển khai sau lab:

1. Đánh giá ứng viên tiếng cười trên video thực, có đối chứng chọn ngẫu nhiên và đỉnh âm lượng. Nếu embedding không hơn baseline, chưa mở rộng nó.
2. Thêm transcript tiếng Việt local và timestamp câu để khôi phục phần dẫn/chốt câu chuyện. Đo lỗi nhận dạng từ tiếng lóng, nói đè và tên game.
3. Gộp tín hiệu hình/âm thanh/transcript bằng một phương pháp có thể đánh giá. Không cộng cosine của các modality một cách tùy ý; thử xếp hạng theo thứ hạng hoặc chuẩn hóa trên tập validation, báo riêng đóng góp từng phần.
4. Nhập marker nếu có, gộp các ứng viên trùng và cho sửa biên đoạn. Giữ bộ lựa chọn trước khi đầu tư phụ đề, crop dọc hay hiệu ứng.
5. Chỉ thêm xếp hạng theo gu của editor khi đã có đủ lượt giữ/bỏ và tập kiểm thử tách theo video; không gọi việc lưu feedback là model đã tự học.

## Pilot để xác nhận pain point

Mục tiêu đề xuất, chưa đạt: một editor hoàn thành danh sách clip được chấp nhận nhanh hơn ít nhất 50% so với cách hiện tại, tính cả việc kiểm tra những đề xuất sai. Đo riêng lần đầu có chi phí xử lý và những lần tìm lại trên thư viện đã index.

Trước khi coi là sản phẩm hữu ích:

- Thử với 3–5 người thực sự dựng video dài, ít nhất 3 video mỗi người. Đây là kế hoạch tuyển pilot, chưa có người tham gia.
- Thu thập thời gian rà video, số ứng viên phải xem, số đoạn giữ được, mức phải sửa biên và số cảnh quan trọng bị bỏ sót. Có thể một người chọn vì hài, người khác vì kể chuyện: giữ lý do thay vì ép một nhãn tuyệt đối.
- So sánh với workflow của họ gồm marker/transcript nếu vốn có; không tạo baseline yếu bằng cách bắt họ xem toàn bộ tốc độ 1x.
- Dùng video chưa từng chỉnh ngưỡng; đảo thứ tự điều kiện và tác vụ để giảm hiệu ứng nhớ trước. Video YouTube đang có không mặc định đại diện VOD thô.
- Đo Precision@10 theo quyết định editor, recall với danh sách cảnh họ đã chọn độc lập, tỷ lệ đoạn đủ dẫn/kết, và thời gian đến bản chọn cảnh cuối. Đánh giá sự đồng thuận giữa người chọn nếu dùng từ “hay nhất”.
- Nếu marker đã giải quyết phần lớn vấn đề, ưu tiên nhập marker và bàn giao. Nếu họ mất thời gian chủ yếu ở dựng nhịp/hiệu ứng, cần điều chỉnh sản phẩm thay vì tiếp tục tăng độ phức tạp retrieval.

## Phương pháp nghiên cứu

9 lượt Exa, mỗi lượt yêu cầu 5 kết quả, theo nhu cầu creator/editor, bóng đá và khả năng model/dữ liệu. Ưu tiên trải nghiệm editor trực tiếp, tài liệu nền tảng, tài liệu dự án và nghiên cứu gốc. Nguồn nhà cung cấp chỉ chứng minh cách sản phẩm được mô tả, không chứng minh hiệu quả độc lập. Những bài marketing AI clip chỉ được dùng để khám phá hướng tìm, không làm bằng chứng tiết kiệm thời gian.

Lượt này có thử nghiệm local và một giao diện duyệt hoạt động; chưa có đánh giá người dùng, chưa thử video bóng đá, chưa có ASR hay xếp hạng hài hước trong sản phẩm desktop chính.

## Bằng chứng chạy thực tế

- Toàn bộ audio 7.886,356 giây được chia thành 789 cửa sổ, 10 giây/cửa sổ, cửa sổ cuối ngắn hơn. Job đầu chạy 12 cửa sổ, job tiếp theo dùng checkpoint và chạy 777 cửa sổ còn lại.
- Tổng thời gian đo riêng các lần encode audio là 104,522 giây. Không gồm tải dữ liệu đối chứng, giải mã nguồn, tải model, xử lý đối chứng, tạo clip hoặc thời gian người dùng duyệt; không gọi đây là tổng thời gian xử lý video. Tải model của lượt tiếp tục mất 3,880 giây.
- Runtime PyTorch 2.14.1+cu126, RTX 3050 Ti 4 GB, EG2 text+audio BF16; peak CUDA allocated của tiến trình lab khoảng 1.140,56 MiB. Con số không bao gồm VRAM của app chính hoặc driver. App chính vẫn chạy trong lúc thử.
- Truy vấn tiếng cười EN có top 3 tại 50:50, 02:00, 07:40; VI tại 50:50, 07:40, 31:40. Đây là kết quả tìm kiếm chưa được gán nhãn chất lượng.
- Câu “khoảnh khắc hài hước nhất” trả top 3 audio tại 1:56:10, 2:09:50, 45:20. Việc khác kết quả tiếng cười cho thấy hai câu truy vấn có hành vi khác nhau; không chứng minh nhóm nào hay hơn.
- Baseline hình ảnh hiện tại được chạy lại với bốn câu hỏi. Hai câu tiếng cười đều trả ảnh tại 1:51:10 lên đầu; audio trả 50:50. Không dùng khác biệt thứ hạng này làm thước đo accuracy vì chưa có nhãn trên nguồn thực.
- 10 ứng viên sau gộp các cửa sổ trùng được xuất thành 10 clip xem lại, mỗi clip 40 giây, tổng 82.834.285 byte. Cả 10 clip giải mã hoàn toàn bằng FFmpeg không lỗi. Kích thước/mtime video gốc không đổi.
- UI đã kiểm tra: chọn 50:50, video 960px/40 giây, `readyState=4`, `paused=true`, `muted=true`; giữ và ghi chú còn sau reload; JSON xuất chứa 10 ứng viên và một lựa chọn kiểm thử; CSV có đúng một hàng đã giữ. Đã đưa lựa chọn kiểm thử về chưa duyệt và xóa ghi chú kiểm thử trong lab trước khi bàn giao. Không đánh đồng thao tác này với duyệt nội dung.
- Console UI không có warning/error trong lượt kiểm tra. Hai script qua `py_compile`; thay đổi không đụng worker/UI desktop chính nên không chạy lại toàn bộ suite desktop.

Lab dùng server Vite preview hiện có tại `http://127.0.0.1:1420/highlight-lab-20261101/`; bản phục vụ nằm trong `desktop/dist/` bị Git bỏ qua. Build frontend mới có thể xóa bản này; bản gốc tái tạo nằm trong `outputs/highlight-lab/review/`. Không phát âm thanh hoặc mở cửa sổ native khi kiểm thử.

Bằng chứng local: `outputs/highlight-lab/audio/candidates.json`, `control-report.json`, `audio-vectors.npz`, `visual-baseline/report.json`, `review/review-manifest.json`, `clip-integrity.json`, `review-lab.png`. Các file âm thanh, hình và video không thuộc Git.

Chạy lại bằng runtime CUDA đã đóng gói:

```powershell
& outputs/releases/FrameAtlas-CUDA/runtime/python.exe scripts/probe_highlight_audio.py `
  --source '<đường dẫn video local>' --model data/models/embeddinggemma-2 `
  --ffmpeg outputs/releases/FrameAtlas-CUDA/runtime/ffmpeg.exe --output outputs/highlight-lab/audio
& outputs/releases/FrameAtlas-CUDA/runtime/python.exe scripts/build_highlight_review.py `
  --lab outputs/highlight-lab/audio --ffmpeg outputs/releases/FrameAtlas-CUDA/runtime/ffmpeg.exe `
  --output outputs/highlight-lab/review
```

Lần đầu cần mạng để tải 32 file ESC-50 cùng metadata/license từ commit đã pin; inference nguồn người dùng chạy local. Dùng thư mục output mới khi đổi source/model. Thay model hoặc cách lấy mẫu cần chạy lại; không dùng cache cũ để so sánh phiên bản khác.
