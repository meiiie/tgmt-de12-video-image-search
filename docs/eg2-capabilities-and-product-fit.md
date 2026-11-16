# EG2: mức độ mở, năng lực thực và lựa chọn ứng dụng

Ngày kiểm tra: 01/11/2026. Model: **EmbeddingGemma 2**, viết tắt EG2; không phải chatbot Gemma 2. Đây là đánh giá năng lực và mức phù hợp của sản phẩm, chưa phải quyết định chuyển FrameAtlas thành một app luyện thi hoặc phân tích cảm xúc.

## Kết luận độc lập

EG2 phù hợp nhất với việc **tìm, xếp hạng và gom các nội dung liên quan trong thư viện chữ/ảnh/video/audio**. Nó cũng có thể cung cấp đặc trưng cho bộ phân loại được huấn luyện theo nhiệm vụ. Điều này tạo cơ hội cho ứng dụng học tập, phân tích phản hồi và chọn cảnh, nhưng không tự chứng minh những ứng dụng đó có khách hàng hoặc đạt chất lượng cần thiết.

Ở các lượt trước, dự án đã chọn hướng giao thông rồi creator quá nhanh từ mức phù hợp kỹ thuật. Bằng chứng hiện có là các phép thử và lab, chưa phải xác nhận nhu cầu thị trường. Giữ các lab làm công cụ kiểm chứng; không đổi toàn bộ sản phẩm theo mỗi ví dụ mới.

## 1. EG2 có hoàn toàn mã nguồn mở không?

Đã kiểm tra metadata và README của đúng revision đang dùng: `f9972ac22e696a105c482202646979e33e4b5a1e` trong repository `google/embeddinggemma-2`.

| Thành phần | Điều xác nhận được |
|---|---|
| Trọng số, tokenizer, cấu hình | Công khai; metadata `gated=false`, `license=apache-2.0` |
| Mã inference | Có implementation đọc được trong Transformers; file local ghi Apache-2.0 |
| Sử dụng/chỉnh sửa/phân phối, kể cả thương mại | Được phép theo Apache-2.0; vẫn phải tuân thủ điều khoản thông báo và phân phối |
| Hướng dẫn fine-tune | Có hướng dẫn chính chủ và code mẫu |
| Mô tả cách huấn luyện | Có model card và technical report mô tả kiến trúc, loss và các giai đoạn |
| Toàn bộ dữ liệu pretraining và pipeline tái tạo chính xác từ đầu | Không tìm thấy được phát hành đầy đủ trong các nguồn và file release đã kiểm tra |

Cách nói chính xác: **model trọng số mở dưới Apache-2.0, có mã chạy và khả năng tùy biến; chưa có cơ sở gọi toàn bộ quá trình tạo model là công khai và tái tạo hoàn toàn**. Có thể chạy local sau khi tải model; không bắt buộc gọi API trả tiền để tạo embedding. Chi phí máy và thành phần khác của sản phẩm là chuyện riêng.

Nguồn: [release đã pin](https://huggingface.co/google/embeddinggemma-2/tree/f9972ac22e696a105c482202646979e33e4b5a1e), [README đã pin](https://huggingface.co/google/embeddinggemma-2/blob/f9972ac22e696a105c482202646979e33e4b5a1e/README.md), [license do Google công bố](https://ai.google.dev/gemma/apache_2), [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), [fine-tuning chính chủ](https://ai.google.dev/gemma/docs/embeddinggemma/fine-tuning-embeddinggemma-with-sentence-transformers).

Giấy phép của EG2 không tự cấp quyền dùng mọi video, bộ dữ liệu hay model phụ tích hợp trong app. Không suy luận giấy phép EG2 từ giấy phép của một model Gemma khác.

### Số tham số và nơi triển khai

[Model card chính thức](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2) ghi **740 triệu tham số**: văn bản 270M (transformer 130M + embedder 140M), thị giác 170M, âm thanh 300M. Các nhánh có thể nạp riêng. `desktop/backend/inference.py` đặt `audio_config=None`, nên app hiện nạp phần chữ + ảnh, khoảng **440M** theo cách chia của model card; không phải đang dùng một model 740M đầy đủ mọi modality. Vector đầu ra đang dùng là 768 chiều.

Có thể tích hợp local/offline sau lần tải trọng số hoặc trên server, kể cả sản phẩm thương mại. Apache-2.0 không bắt buộc công khai toàn bộ mã ứng dụng; khi phân phối phải giữ các thông báo/giấy phép liên quan và ghi nhận thay đổi theo điều khoản. Khả năng chạy trên từng máy phụ thuộc bộ nhớ, runtime và phần cứng; “được phép tích hợp” không có nghĩa mọi thiết bị đều chạy được. Trọng số mở và mã inference công khai cũng không đồng nghĩa toàn bộ dữ liệu/pipeline pretraining đều đã công bố.

## 2. Nó thực hiện thao tác gì?

Một ví dụ: người dùng hỏi bằng tiếng Việt “cách xin người khác nhắc lại chậm hơn”. Thư viện có một đoạn tiếng Anh chứa “Could you say that again more slowly?”. EG2 biến câu hỏi và các đoạn thành vector để hệ thống tìm các nội dung gần nghĩa, rồi ứng dụng mở đoạn nguồn tương ứng.

Từ đó có bốn cách dùng khác nhau:

1. **Retrieval:** trả các đoạn có khả năng liên quan để kiểm tra.
2. **Clustering:** gom phản hồi nói về cùng vấn đề, ví dụ pin, giao hàng hoặc đăng nhập.
3. **Classification:** dùng embedding làm đầu vào cho bộ phân loại học từ nhãn; hoặc thử baseline so với mô tả các nhãn khi chưa fine-tune.
4. **RAG:** tìm bằng chứng rồi đưa cho một model sinh ngôn ngữ để giải thích/trả lời có dẫn nguồn.

Một vector gần câu mẫu không phải chứng nhận đúng kiến thức, đúng ngữ pháp, phát âm tốt hay phù hợp để dạy. Model cũng không tự xuất transcript, lời giải thích hoặc band score chỉ từ đầu ra embedding. [Model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)

Technical report có đánh giá audio trong các nhiệm vụ bao gồm cảm xúc, và có cơ chế xử lý đa phương thức. Vì vậy không nên thu hẹp EG2 thành công cụ chỉ nhìn ảnh tĩnh. Tuy nhiên, kết quả benchmark tổng hợp không xác nhận một bộ chấm IELTS hay phân tích mỉa mai tiếng Việt. [Technical report, phần audio](https://arxiv.org/html/2610.37364v1#S4.SS4)

## 3. Phân tích tích cực/tiêu cực trong video: khả thi, nhưng phải định nghĩa đúng

| Câu hỏi | Ví dụ | Mức phù hợp |
|---|---|---|
| Người nói khen/chê điều gì? | “Camera đẹp nhưng pin quá yếu” | Khả thi cho phân tích quan điểm theo khía cạnh, có transcript/ngữ cảnh |
| Đoạn nào có phàn nàn về pin? | Tìm các câu nói gần nghĩa “pin tụt rất nhanh” | Rất phù hợp làm bài toán tìm kiếm; người dùng kiểm tra đoạn gốc |
| Giọng đang vui, tức giận, buồn? | Người nói lớn tiếng nhưng có thể chỉ đang diễn | Có thể thử phân loại biểu hiện âm thanh; cần nhãn và ngữ cảnh riêng |
| Video có nội dung nguy hiểm/xúc phạm? | Một nội dung có thể vui về âm thanh nhưng vẫn xúc phạm | Là tác vụ nội dung riêng, không dùng polarity tích cực/tiêu cực thay thế |
| Khán giả sẽ thấy tích cực hay tiêu cực? | Một joke được người này thích, người khác khó chịu | Không suy ra trực tiếp từ thái độ người nói; cần dữ liệu khán giả |

Không gắn một nhãn cho cả video dài khi các đoạn và đối tượng được nói đến khác nhau. Câu “camera đẹp nhưng pin yếu” cần giữ hai khía cạnh; một nhãn âm tính toàn câu mất phần khen. Tiếng cười, volume lớn hoặc khuôn mặt không chứng minh trạng thái tâm lý bên trong của một người.

Ứng dụng cụ thể hơn một biểu đồ cảm xúc: **trợ lý rà phản hồi sản phẩm từ các cuộc phỏng vấn/video review**. Người nghiên cứu hỏi “khách hàng đang gặp khó khăn gì khi đăng nhập?”; app gom chủ đề, tìm các trích đoạn, ghi rõ người nói đang nhận xét đối tượng nào và giữ đường dẫn về timestamp. Người dùng đối chiếu bằng chứng trước khi tổng hợp vấn đề.

Pipeline cần kiểm chứng: ASR có timestamp → tách lượt nói/ngữ cảnh → EG2 tìm và gom theo chủ đề → classifier/reranker hoặc model ngôn ngữ xử lý đối tượng, polarity và mỉa mai → hiển thị trích dẫn/clip + trạng thái chưa chắc. ASR không bắt buộc cho mọi truy vấn audio, nhưng giúp kiểm tra lời nói và phân tích khía cạnh ở đây.

CMU-MOSEI có nhãn sentiment riêng với các nhãn emotion, phù hợp làm đối chứng phương pháp; đó là video độc thoại tiếng Anh, không tự đại diện hội thoại Việt có tiếng lóng/nói đè. [MOSEI](https://github.com/CMU-MultiComp-Lab/CMU-MultimodalSDK/blob/main/mmsdk/mmdatasdk/dataset/standard_datasets/CMU_MOSEI/README.md)

[UIT-VSFC](https://huggingface.co/datasets/uitnlp/vietnamese_students_feedback) có nhãn sentiment cho văn bản phản hồi sinh viên tiếng Việt, hữu ích để nghiên cứu một baseline ngôn ngữ. Domain khác video review; metadata license chưa rõ trong nguồn đã đọc, nên chưa dùng để fine-tune sản phẩm thương mại trong lượt này.

## 4. Luyện thi/luyện nói: EG2 là thành phần nào?

| Công việc | EG2 đóng góp | Thành phần khác cần có |
|---|---|---|
| Tìm lại chỗ thầy giải thích một khái niệm | Tìm chữ, hình slide, đoạn audio/video gần yêu cầu | Phân đoạn nguồn và timestamp; có thể dùng ASR/OCR để tăng khả năng kiểm tra |
| Tìm câu mẫu theo tình huống giao tiếp | Tìm các ví dụ gần ý định | Nhãn/ngữ dụng/reranker kiểm tra lịch sự, độ khó và độ đúng |
| Tạo bộ ôn từ những đoạn đã học | Gom các đoạn liên quan, tìm nguồn | Công cụ tạo bài tập, đáp án, lưu lịch ôn; kiểm tra chất lượng câu hỏi |
| Nhận biết đang lạc đề | Hỗ trợ đo mức liên quan với đề | Xem cấu trúc và nội dung toàn câu trả lời; không quy similarity thành điểm |
| Chỉ ra sai âm, trọng âm, nối âm | Có thể nghiên cứu embedding như một loại feature | Speech model, căn chỉnh âm vị, nhãn phát âm và phép đánh giá phù hợp |
| Chấm IELTS Speaking | Truy hồi rubric/ví dụ tham chiếu | Đánh giá bốn tiêu chí, dữ liệu chuyên gia và kiểm định độc lập |

IELTS Speaking đánh giá độ trôi chảy/mạch lạc, từ vựng, ngữ pháp và phát âm. Một câu nói gần nghĩa với mẫu không thể thay bốn tiêu chí này. [IELTS chính thức](https://ielts.org/take-a-test/test-types/ielts-general-training-test/ielts-general-training-format-speaking)

SpeechOcean762 minh họa dữ liệu cần cho chấm phát âm: nhãn chuyên gia ở mức câu, từ và âm vị. Người nói trong bộ này có tiếng mẹ đẻ Mandarin; dùng được để thử kỹ thuật không có nghĩa đã phù hợp người Việt hoặc toàn bộ Speaking tự do. [SpeechOcean762](https://github.com/jimbozhang/speechocean762)

**Nếu ưu tiên việc học, tôi chọn công việc hẹp:** người học có nhiều bài giảng/video, nhớ ý nhưng không nhớ nằm ở đâu; tìm đúng đoạn, nghe/xem lại, lưu dẫn chứng và luyện với đoạn đó. Đầu ra đầu tiên là đoạn nguồn đúng và lịch sử ôn, chưa cần chấm band tự động.

Tuy vậy, thị trường đã có [Language Reactor](https://www.languagereactor.com/help/tips) cho thao tác nghe lại/lưu câu và [NotebookLM/Gemini Notebook](https://support.google.com/notebooklm/answer/16215270?co=GENIE.Platform%3DDesktop&hl=en) cho học từ nhiều loại nguồn. Không mặc định thêm AI vào phụ đề là khác biệt đủ lớn. Cần thử giá trị của thư viện video local, truy tìm cả hình/âm thanh và trả về chính xác đoạn gốc. Chưa có thử nghiệm đối đầu sản phẩm hoặc người học thực trong lượt này.

## 5. Phép thử trực tiếp trên EG2

Để không chỉ lập luận từ tài liệu, đã khai báo bộ chẩn đoán trước khi chạy tại `docs/lab/eg2-capability-cases.json` và chạy `scripts/probe_eg2_capabilities.py`. Tất cả ví dụ do agent tự soạn; không phải benchmark đại diện, không là ground truth đánh giá con người, không kiểm tra audio phát âm.

Thiết lập: model local đã pin; chỉ text encoder/backbone; CUDA trên RTX 3050 Ti; 768 chiều, chuẩn hóa FP32. Chạy BF16 rồi chạy lại FP32 vì một số chênh lệch cosine nhỏ. Không sửa câu hỏi/nhãn để cải thiện kết quả sau khi xem đầu ra.

| Phép thử | Kết quả BF16 | Kết quả FP32 | Phạm vi kết luận |
|---|---|---|---|
| Phân loại 16 câu thông thường thành khen/chê/trung lập/hỗn hợp | 14/16 đúng | 14/16 đúng | Một baseline zero-shot nhỏ, chưa đo video |
| 8 câu phủ định, mỉa mai, tương phản | 6/8 đúng | 6/8 đúng | Có trường hợp hiểu đúng và có lỗi ngữ cảnh |
| 6 cặp đáp án đúng/sai so với câu tham chiếu | Câu sai có similarity cao hơn trong 4/6 cặp | Cùng 4/6 cặp | Cosine không phải phép chấm đúng/sai |
| 6 truy vấn Việt tìm ví dụ giao tiếp trong 12 câu Anh | 5/6 top-1 đúng | 5/6 top-1 đúng | Tìm được ý định thường gặp nhưng có lỗi sắc thái |

Sentiment dùng `Classification` cho cả câu và mô tả nhãn; đã thử hai bộ mô tả nhãn EN/VI và nhận cùng các dự đoán sai. STS dùng `STS` cho cả câu tham chiếu/ứng viên. Retrieval dùng `SearchQuery` cho truy vấn và `Document` cho corpus. Không lấy mặc định SearchQuery cho mọi việc, cũng không huấn luyện classifier riêng trong phép thử này.

Lỗi cần giữ lại:

- “Fantastic, the app deleted all my work again. Just what I needed!” bị chọn **positive**, dù nhãn dự kiến là chê mỉa mai.
- Ba câu có cả khen và chê bị chọn **negative**, bỏ mất khía cạnh tích cực.
- Truy vấn tìm cách từ chối lịch sự xếp “No. Stop bothering me with your invitation.” trên “Thank you for inviting me. I'd love to join, but I already have plans that evening.”; câu đúng ở hạng 2. Đây là lý do cần kiểm tra sắc thái trước khi đưa thành câu nên học.
- Với câu mẫu “You should turn left after the bridge.”, FP32 cho câu sai “You should turn right after the bridge.” cosine **0,976695**, cao hơn diễn đạt đúng “Once you have crossed the bridge, take the road on your left.” **0,960271**.
- Câu sai ngữ pháp “I goed to the cinema yesterday.” cũng gần câu mẫu hơn diễn đạt đúng tương đương trong phép thử; lỗi thứ hạng vẫn còn ở FP32.

Các trường hợp này chứng minh cách dùng similarity làm điểm chấm có phản ví dụ. Chúng không chứng minh mọi classifier huấn luyện trên EG2 đều thất bại, cũng không ước lượng lỗi ngoài thực tế. Tiếp tục tối ưu cần tập dữ liệu tách biệt, nhãn do người phù hợp xác nhận và baseline model chuyên nhiệm vụ; không chỉnh prompt theo các ví dụ này rồi báo thành công trên chính chúng.

## 6. Ưu tiên nào có cơ sở nhất?

| Hướng | Mức phù hợp trực tiếp với EG2 | Điều chưa biết | Quyết định hiện tại |
|---|---|---|---|
| Truy tìm bằng chứng/đoạn đã xem trong video local | Cao: đúng mục tiêu retrieval đa phương thức | Có nhanh/hữu ích hơn workflow hiện tại không? | Giữ làm lõi sản phẩm và đơn vị kiểm chứng |
| Chọn ứng viên clip cho editor | Vừa: EG2 hỗ trợ thu hẹp, gu dựng cần thêm ngữ cảnh | Precision theo editor, tỷ lệ bỏ sót, thời gian duyệt | Giữ lab có video thật, tiếp tục đo |
| Gom và tìm lời khen/chê về từng khía cạnh | Vừa: topic/retrieval thuận lợi; sentiment cần nhãn | Domain tiếng Việt, nói đè, mỉa mai, nhu cầu người nghiên cứu | Thử như một workflow có trích dẫn, chưa làm dashboard cảm xúc tổng quát |
| Trợ lý học từ thư viện video cá nhân | Cao cho tìm đoạn; vừa cho hoạt động học | Lợi thế so với công cụ đã có, nguồn dữ liệu thực | Đáng pilot khi có bài học/tác vụ cụ thể, không tự chuyển toàn app |
| Chấm IELTS/phát âm hoặc chọn “hay nhất” bằng cosine | Thấp với cách làm trực tiếp này | Thiếu model chuyên biệt và nhãn đánh giá | Không dùng làm lời hứa sản phẩm hiện tại |

Đây là đánh giá kỹ thuật và phạm vi bằng chứng, không phải chấm điểm cơ hội kinh doanh. EG2 là một bộ phận; nếu công việc đích là chấm nói, phải chọn công nghệ từ yêu cầu chấm nói thay vì ép mọi việc vào EG2.

## 7. Bước kiểm chứng tiếp theo và tiêu chí dừng

1. **Giữ một lõi tìm đoạn có dẫn nguồn.** Thêm transcript với timestamp có ích cho cả học tập, creator và rà phản hồi; đo lỗi và thời gian xử lý trên audio Việt thật trước khi chọn ASR.
2. **Định nghĩa tác vụ người dùng trước model mới.** Ví dụ: tìm lại đoạn giải thích cụ thể trong nhiều bài giảng; tìm những lời chê pin trong 10 video review; lập danh sách cảnh editor chấp nhận. Không so các ngành bằng một điểm “AI có vẻ làm được”.
3. **So với cách hiện tại.** Tua tay, tìm trong phụ đề, marker và công cụ người dùng vốn có. Đo tỷ lệ tìm đúng nguồn và thời gian hoàn thành, tính cả sửa kết quả sai.
4. **Nếu thử sentiment:** gán nhãn đối tượng/khía cạnh, tích cực/tiêu cực/trung lập/hỗn hợp/chưa rõ; tách theo video/người nói. Đo macro-F1, từng lớp, lỗi mỉa mai và khả năng bỏ ngỏ. Mỗi nhãn phải truy về câu/clip.
5. **Nếu thử hỗ trợ nói:** trước hết kiểm chứng tìm câu đúng tình huống và nội dung phản hồi bằng người có chuyên môn. Pronunciation cần nhãn mức âm/từ và đánh giá trên người Việt; band score cần bộ đối chiếu giám khảo. Không lấy cosine, tốc độ nói hoặc transcript giống nhau làm điểm thi.
6. **Dừng mở rộng khi chưa có lợi ích tác vụ.** Nếu người dùng tìm bằng phụ đề nhanh hơn và chính xác hơn, ưu tiên tích hợp phụ đề/marker. Nếu bộ gán sentiment khiến họ sửa nhiều hơn đọc tay, dùng EG2 để gom/tìm bằng chứng trước.

## Bằng chứng và tái chạy

- Bộ ví dụ: `docs/lab/eg2-capability-cases.json`.
- Script: `scripts/probe_eg2_capabilities.py`.
- Kết quả local đầy đủ: `outputs/capability-lab/results.json`, `results-fp32.json`.
- Bản kết quả không chứa đường dẫn local: `results/eg2-capabilities-20261101.json`.
- Hai lần chạy dùng cùng SHA-256 bộ ví dụ; bảng tổng hợp và các lỗi đối chiếu trực tiếp từ JSON. Không thay model, nguồn video hoặc chỉ mục của app.

```powershell
& outputs/releases/FrameAtlas-CUDA/runtime/python.exe scripts/probe_eg2_capabilities.py `
  --model data/models/embeddinggemma-2 --cases docs/lab/eg2-capability-cases.json `
  --output outputs/capability-lab/results.json
& outputs/releases/FrameAtlas-CUDA/runtime/python.exe scripts/probe_eg2_capabilities.py `
  --model data/models/embeddinggemma-2 --cases docs/lab/eg2-capability-cases.json `
  --output outputs/capability-lab/results-fp32.json --dtype fp32
```

Nghiên cứu dùng 9 lượt Exa (45 vị trí kết quả, có nguồn trùng) và đọc nguồn gốc; web fetch dùng bổ sung khi trang license timeout và để đọc technical report. Không coi số kết quả tìm kiếm là số công trình đã đọc trọn. Chỉ agent chính thực hiện, không dùng subagent, không bật mic hay phát âm thanh, không upload media người dùng.
