# Lời thuyết trình FrameAtlas — EG2 và phần triển khai

Trình bày 25 trang chính trong khoảng 15 phút. Năm trang cuối là phụ lục dành cho hỏi đáp; không cần trình bày hết trong phần chính. Thời gian từng trang là hướng dẫn.

## 01. Có một tấm ảnh.
Tìm lại đoạn video
Trang 01 · Gợi ý 18 giây



## 02. Bạn sẽ tua đến đâu?
Trang 02 · Gợi ý 33 giây

Đây là bức ảnh em muốn tìm. Trong ảnh có một tấm biển quảng cáo màu đỏ, chữ trắng và hình những người ở bên phải.
Em biết cảnh này nằm trong video road1.mp4, nhưng video dài tới 33 phút 36 giây. Nếu tự mở video rồi tua từng đoạn, em sẽ phải mất khá nhiều thời gian mới tìm thấy tấm biển.
Vì vậy, em đưa bức ảnh này vào FrameAtlas và yêu cầu chương trình tìm trong video road1.mp4. Mục tiêu là biết tấm biển nằm ở thời điểm nào.

## 03. FrameAtlas tìm thấy biển ở 20:41,24
Trang 03 · Gợi ý 35 giây

Đây là kết quả chương trình tìm được. Bên trái là ảnh em gửi, còn bên phải là một khung hình trong video road1.mp4.
Các bạn có thể thấy tấm biển đỏ xuất hiện ở phía trên đường. Dù trong video tấm biển nhỏ hơn ảnh em đưa vào, chương trình vẫn tìm được khung có nội dung phù hợp
Kết quả đứng đầu đưa em đến phút 20, giây 41,24.
Để làm được việc đó, FrameAtlas thực hiện ba bước: chọn khung hình từ video, so sánh hình ảnh, rồi mở lại video tại mốc đã tìm.

## 04. Video dài được tách thành các khung để tra
Trang 04 · Gợi ý 39 giây

Video thực chất là rất nhiều khung hình nối tiếp nhau. Mỗi khung giống như một bức ảnh tĩnh tại một thời điểm trong video.
Trên slide, em chọn năm khung ở những vị trí khác nhau để các bạn thấy cảnh trong video đã thay đổi: lúc có vật thể màu cam, lúc có giàn giáo, rồi đến biển quảng cáo và những cảnh khác.
Khi chuẩn bị video, cứ khoảng hai giây, chương trình chọn một khung hình để xử lý. Mỗi khung được chuyển thành dãy số và lưu kèm mốc thời gian. Với video road1.mp4, hệ thống đã lưu được 1.007 khung hình để phục vụ tìm kiếm.

## 05. Khoảng 2 giây vẫn có thể bỏ sót chi tiết
Trang 05 · Gợi ý 47 giây

Ba ảnh này cách nhau khoảng hai giây. Ở ảnh đầu, tấm biển còn ở xa. Đến ảnh giữa, biển hiện ra rõ hơn. Nhưng sang ảnh cuối, cột phía trước đã che mất một phần biển. Điều đó cho thấy chỉ trong vài giây, hình ảnh có thể thay đổi rất nhiều. Nếu một vật chỉ xuất hiện giữa hai thời điểm được chọn, chương trình có thể bỏ sót vật đó.
Để hạn chế điều này, dự án còn có cách lấy mẫu kết hợp: dùng FFmpeg phát hiện chỗ chuyển sang cảnh mới, rồi bổ sung khung gần đầu cảnh khi cần. Tuy nhiên, ca road1.mp4 trên slide này dùng lấy mẫu đều. Nếu vật bị che ngay trong cùng một cảnh quay, phát hiện chuyển cảnh cũng chưa chắc giúp được.

## 06. Mỗi khung mang theo địa chỉ của nó
Trang 06 · Gợi ý 39 giây

Mỗi khung hình được lưu cùng một bộ thông tin. Em gọi đơn giản đây là tấm thẻ của khung. Trong thẻ có một dãy gồm 768 số để máy tính so sánh hình ảnh.
Ngoài ra còn có thông tin cho biết khung thuộc video nào và nằm ở thời điểm nào. Ví dụ, khung này thuộc road1.mp4, tại phút 20, giây 41,24.
Chương trình lưu các thông tin quản lý trong SQLite, là cơ sở dữ liệu nằm ngay trên máy tính. Nhờ đó, khi tìm được khung phù hợp, chương trình không chỉ hiện ra bức ảnh mà còn biết phải mở video nào, ở giây nào.

## 07. Chuẩn bị một lần, dùng cho nhiều lượt tìm
Trang 07 · Gợi ý 40 giây

Các bạn có thể hình dung quá trình chuẩn bị video như một dây chuyền gồm ba bước.
Đầu tiên, chương trình chọn và đọc những khung hình cần giữ.
Tiếp theo, mô hình AI chuyển từng khung thành một dãy số.
 Cuối cùng, chương trình lưu dãy số đó cùng tên video và thời điểm của khung
.Quá trình này gọi là lập chỉ mục. Điểm tiện lợi là chúng ta chỉ cần chuẩn bị dữ liệu video trước. Sau đó, mỗi lần đổi ảnh cần tìm, chương trình không phải mã hóa lại tất cả khung của video. Nó chỉ cần mã hóa ảnh mới và so sánh với dữ liệu đã lưu.

## 08. EG2 là mô hình tạo biểu diễn nội dung
Trang 08 · Gợi ý 30 giây

EG2 là tên viết tắt của EmbeddingGemma 2, mô hình tạo biểu diễn nội dung do Google DeepMind phát triển. Với một ảnh, mô hình trả về một vector gồm 768 số. Các số mô tả đặc trưng đã học, không phải 768 điểm ảnh hay 768 tên đối tượng. Mô hình hỗ trợ nhiều loại dữ liệu; đề tài dùng ảnh và câu chữ. EG2 chưa cho biết tên video hay thời điểm. Hai thông tin đó do chương trình gắn vào chỉ mục.

Nguồn: Google DeepMind · Tài liệu mô hình EG2 [1] · Đối chiếu ngày 14/11/2026
https://huggingface.co/google/embeddinggemma-2

## 09. Vì sao ảnh liên quan có vector gần nhau?
Trang 09 · Gợi ý 33 giây

Trong quá trình huấn luyện của nhà phát triển, một mục tiêu quan trọng là học tương phản: đưa biểu diễn của cặp có liên hệ lại gần và tách các cặp khác nhau ra. Nhờ trọng số đã học, ảnh mới cũng có thể được biểu diễn theo cách này. Ba ảnh road1 chỉ minh họa nguyên tắc; không phải dữ liệu huấn luyện EG2 hay tọa độ vector đã đo. Khi thêm video vào FrameAtlas, em sử dụng trọng số có sẵn để tạo chỉ mục, không huấn luyện lại mô hình.

Nguồn: Sơ đồ minh họa mục tiêu học tương phản [2]; ảnh từ ca road1 của đề tài.
https://arxiv.org/html/2610.37364v2

## 10. EG2 biến ảnh thành vector như thế nào?
Trang 10 · Gợi ý 35 giây

Ảnh được chuyển về hệ màu RGB, nghĩa là đỏ, xanh lá và xanh lam. Bộ mã hóa thị giác rút ra chuỗi đặc trưng ảnh. Transformer xử lý quan hệ trong chuỗi này. Phần gộp trung bình và lớp chiếu chuyển biểu diễn 512 thành 768 thành phần; sau đó vector được chuẩn hóa độ dài. Phim là sơ đồ rút gọn các bước, không phải máy phần cứng hay từng phép tính thực tế. Trong mã dự án, thư viện thực hiện phần bên trong; em kiểm soát đầu vào, cấu hình và kiểm tra đầu ra.

Nguồn: Kiến trúc rút gọn từ tài liệu mô hình [1], [2].
https://huggingface.co/google/embeddinggemma-2
https://arxiv.org/html/2610.37364v2

## 11. Bằng chứng để chọn EG2 toàn khung
Trang 11 · Gợi ý 35 giây

Bộ thử nghiên cứu gồm 70 video và 58 truy vấn khó. Kết quả phù hợp phải trùng video và giao với đoạn nhãn nới biên nửa giây. DINOv3 cùng lưới vùng đạt R tại một bằng 0,586; EG2 toàn khung đạt 0,948; EG2 cùng lưới đạt 0,810. R tại một là tỷ lệ truy vấn có kết quả phù hợp ở vị trí đầu. Đề tài chọn EG2 toàn khung trong điều kiện này. Kết quả không chứng minh EG2 luôn tốt nhất; chất lượng và chi phí trên ứng dụng thật vẫn cần đánh giá riêng.

Nguồn: Phép thử nghiên cứu v7 của đề tài · 70 video, 58 truy vấn khó · Trục cột từ 0 đến 1.

## 12. Vì sao chọn EG2 cho FrameAtlas?
Trang 12 · Gợi ý 38 giây

Em chọn EG2 dựa trên độ phù hợp và kết quả thử, không chỉ vì có sẵn thư viện. Cùng một không gian cho ảnh và chữ hỗ trợ cả hai cách truy vấn. Mô hình chạy trên máy người dùng và cho phép không nạp nhánh âm thanh. Bản đầy đủ khoảng 740 triệu tham số; tài liệu mô hình nêu cấu hình ảnh và chữ khoảng 440 triệu tham số hiệu dụng. Kết quả R tại một vừa trình bày hỗ trợ lựa chọn toàn khung trong bộ thử đó. Chi phí tính toán và ảnh cắt vẫn là những đánh đổi cần kiểm tra.

Nguồn: Căn cứ: tài liệu EG2 [1] và phép thử nghiên cứu v7 của đề tài.
https://huggingface.co/google/embeddinggemma-2

## 13. Cùng một mô hình đọc cả hai ảnh
Trang 13 · Gợi ý 53 giây

Vậy khi người dùng đưa vào một ảnh mới, chương trình so sánh bằng cách nào?
Ở đây, bên trái là ảnh tấm biển cần tìm. Bên phải là khung hình đã lấy từ video, có cả đường phố và tấm biển.
 FrameAtlas sử dụng cùng một mô hình AI tên là EmbeddingGemma 2, viết tắt EG2, để biến mỗi ảnh thành dãy 768 số. Dãy số của khung video đã được tính và lưu trước đó.
 Khi em bấm tìm, chương trình mới tính dãy số cho ảnh bên trái. Vì hai dãy số được tạo theo cùng cách biểu diễn, chương trình có thể đem chúng ra so sánh. Dải màu ở dưới chỉ minh họa các con số, không phải màu thật của bức ảnh.

Cùng Encoder.images được dùng cho ảnh truy vấn và khung trong chỉ mục. Không so vector từ hai cấu hình mô hình khác nhau.

## 14. Áp dụng EG2 trong mã xử lý ảnh
Trang 14 · Gợi ý 34 giây

Đây là đoạn rút gọn từ Encoder.images trong inference.py. SentenceTransformer nạp EG2 và tắt nhánh âm thanh. Ảnh chuyển về RGB; token thị giác là đơn vị đặc trưng trung gian, ngân sách 140 điều chỉnh lượng xử lý ảnh, khác với 768 chiều đầu ra. Với B ảnh, kết quả phải có B hàng và 768 cột. Cấu hình dùng lô bốn. CPU dùng FP32, số thực 32 bit; GPU hỗ trợ thì dùng BF16, dạng bfloat16 có miền giá trị rộng. Chương trình kiểm tra giá trị hữu hạn và chuẩn vector trước khi lưu.

Nguồn: Trích rút gọn: desktop/backend/inference.py · Cấu hình chạy của đề tài.
https://huggingface.co/google/embeddinggemma-2

## 15. Hai dãy số gần hướng thì điểm cao
Trang 15 · Gợi ý 44 giây

Để giải thích cách so sánh, em vẽ mỗi dãy số thành một mũi tên.
Mũi tên vàng là ảnh em muốn tìm. Mũi xanh ngọc có hướng gần với mũi vàng hơn, nên nhận điểm tương đồng cao hơn. Còn mũi xanh nhạt lệch hướng nhiều hơn nên có điểm thấp hơn. Cách đo độ gần về hướng này gọi là độ tương đồng cosine, đọc là cô-sin.
Trước khi so sánh, chương trình chuẩn hóa độ dài của các vector. Ở đây em chỉ vẽ trên mặt phẳng hai chiều cho dễ nhìn. Trong chương trình, mỗi ảnh có tới 768 số. Điểm càng cao nghĩa là hai ảnh càng gần nhau theo cách mô hình biểu diễn, chứ không phải xác suất ảnh đúng.

## 16. Tìm kiếm bằng một phép nhân ma trận
Trang 16 · Gợi ý 33 giây

X có một hàng cho mỗi khung trong phạm vi tìm, q là vector ảnh mới và s là danh sách điểm. Vì vector có độ dài một, tích vô hướng cho điểm cosine. Bản desktop dùng NumPy; FAISS thuộc nhánh nghiên cứu cũ. Tìm tương tự không giải mã lại từng video. Các yêu cầu tìm xử lý lần lượt bằng khóa; thư viện tính toán có thể dùng nhiều luồng nội bộ. Sau chấm điểm, chương trình đếm khung qua ngưỡng theo video, xếp hạng rồi gộp các mốc gần nhau.

Nguồn: Mã thực: desktop/backend/library.py · NumPy matrix @ q.
https://numpy.org/doc/stable/reference/generated/numpy.matmul.html

## 17. Điểm cao giúp chọn khung để xem kỹ
Trang 17 · Gợi ý 44 giây

Đây là một vài kết quả thật khi em tìm tấm biển đỏ trong road1.mp4.
Kết quả đứng đầu ở khoảng 20 phút 41 giây có điểm tương đồng 0,800.Kết quả thứ hai cũng có tấm biển đó nhưng được nhìn từ góc khác, với điểm gần bằng.
Còn kết quả thứ tư có điểm 0,738. Các bạn nhìn kỹ kết quả thứ tư sẽ thấy đó là một biển quảng cáo khác. Vì nó cũng có bảng lớn và hình người, mô hình vẫn cho điểm khá cao.
Vậy nên điểm tương đồng giúp tìm những khung đáng xem trước, nhưng chưa đủ để khẳng định đó chính xác là tấm biển cần tìm. Chương trình còn một bước kiểm tra chi tiết hơn.

## 18. Giống nội dung rồi mới kiểm tra chi tiết
Trang 18 · Gợi ý 44 giây

Bên trái là một kết quả được gợi ý vì có biển lớn và hình người, khá giống về bố cục. Nhưng khi nhìn kỹ, đây không phải tấm biển trong ảnh em gửi. Bên phải mới là biển cần tìm, với cùng dòng chữ và những gương mặt giống ảnh truy vấn.
 Để phân biệt hai trường hợp này, FrameAtlas chọn tối đa 48 khung có triển vọng rồi kiểm tra kỹ hơn. Trong lần tìm trên slide, chương trình đã xác nhận được 7 khung. Khung đứng đầu ở mốc 20:41,24 có 107 điểm khớp qua bước kiểm tra hình học. Nói đơn giản, bước đầu tìm ảnh có vẻ giống; bước sau kiểm tra xem các chi tiết có thực sự khớp nhau không.

## 19. Máy so chữ và các chi tiết nằm cùng chỗ
Trang 19 · Gợi ý 30 giây

SIFT, viết đầy đủ Scale-Invariant Feature Transform, trích đặc trưng cục bộ ở góc, cạnh và họa tiết. RANSAC, Random Sample Consensus, ước lượng một phép biến đổi hình học nhất quán để loại cặp khớp lệch. Trong ca road1, bộ đối chiếu ghi nhận 107 điểm đồng thuận tại mốc đứng đầu. Đây là kiểm tra chi tiết, không nhận dạng nội dung chữ bằng OCR. Ảnh ít họa tiết hoặc đổi góc mạnh vẫn có thể bị từ chối.

Mã: desktop/backend/verification.py.

## 20. Đọc địa chỉ khung để mở video
Trang 20 · Gợi ý 40 giây

Sau khi tìm được khung phù hợp, việc tiếp theo là mở lại video thật.
Đầu tiên, giao diện gửi ảnh cần tìm và phạm vi video cho bộ xử lý trên máy. Bộ xử lý so sánh ảnh, xếp hạng các khung và trả về kết quả.
Mỗi kết quả có thông tin rất quan trọng: mã video và mốc thời gian. Chẳng hạn, kết quả này thuộc road1.mp4 và nằm ở 20 phút 41,24 giây.
Giao diện dựa vào thông tin đã lưu để mở đúng tệp video, rồi chuyển trình phát đến gần thời điểm đó. Người dùng có thể xem lại cảnh thực tế để xác nhận kết quả

## 21. Mở đoạn phố tại mốc tìm được
Trang 21 · Gợi ý 30 giây

Đây là đoạn video được mở từ kết quả đứng đầu mà chúng ta vừa tìm.Các bạn hãy nhìn lên phía trên đường. Tấm biển đỏ xuất hiện trong cảnh, rồi khi góc quay thay đổi thì có lúc bị cột che mất một phần.Điều cần chú ý là chương trình không chỉ trả về một bức ảnh gần giống. Nó còn đưa chúng ta trở lại chính video nguồn để xem cảnh xung quanh.Đoạn clip được trích để minh họa khoảng bảy giây.

## 22. Cắt đủ để còn chữ và gương mặt
Trang 22 · Gợi ý 47 giây

Hai hình này cũng được dùng để thử tìm trong road1.mp4, bằng cùng chế độ đối chiếu chi tiết.
Ảnh bên trái còn cả dòng chữ và gương mặt trên biển, có kích thước 250 nhân 153 điểm ảnh. Với ảnh này, chương trình xác nhận được bảy khung.
Ảnh bên phải bị cắt rất hẹp, chỉ còn một mẩu chữ kích thước 34 nhân 35 điểm ảnh. Kết quả là không có khung nào vượt qua bước kiểm tra chi tiết trong lượt thử đó.
Điều này không có nghĩa tấm biển không tồn tại trong video. Nó chỉ cho thấy ảnh quá nhỏ có thể không còn đủ chi tiết để đối chiếu. Vì vậy, khi tìm bằng ảnh cắt, chúng ta nên giữ đủ phần chữ, hình và một chút bối cảnh

## 23. Thử lại ngay trong FrameAtlas
Trang 23 · Gợi ý 40 giây

Bây giờ em tóm tắt cách người dùng tự thực hiện việc tìm kiếm.Trước hết, mở FrameAtlas và chọn video road1.mp4 trong phần phạm vi tìm.
Tiếp theo, tải ảnh biển quảng cáo lên, dùng toàn ảnh và chọn chế độ Đối chiếu chi tiết ảnh.
Sau khi bấm tìm, chương trình hiện danh sách các khung phù hợp.
Trong ví dụ này, em chọn kết quả đầu ở mốc 20 phút 41,24 giây.Khi video mở ra, chúng ta xem trực tiếp tấm biển trên đường để kiểm tra. Nếu đúng cảnh cần dùng, người dùng còn có thể lưu khoảnh khắc hoặc chọn một khoảng thời gian để xuất thành đoạn video riêng.

## 24. Phần hệ thống xây dựng quanh EG2
Trang 24 · Gợi ý 34 giây

Phần có sẵn là trọng số EG2 và các thư viện nền. Phần triển khai của đề tài là quy trình nối chúng lại thành sản phẩm: chọn lịch khung, đọc theo lô và đọc trước; gắn vector với mã video, thời gian; lưu và tiếp tục công việc; tính điểm, đếm theo video và đối chiếu chi tiết. React, FastAPI và Tauri tạo luồng sử dụng để mở và xuất được nguồn. Đóng góp cần chứng minh bằng mã, phép thử và kết quả sử dụng, không được trình bày thành đã tự huấn luyện EG2.

Nguồn: Đối chiếu các mô-đun library.py, inference.py, store.py, media.py, verification.py và giao diện.

## 25. Vì sao tìm được ảnh trong video?
Trang 25 · Gợi ý 34 giây

Trở lại ảnh biển quảng cáo. EG2 tạo một biểu diễn số cho ảnh, cùng cách đã dùng với các khung video. Chương trình so với ma trận chỉ mục, lấy những khung có điểm cao và đối chiếu chi tiết nếu chọn chế độ này. Bản ghi của khung chứa mã video và mốc thời gian, nên phần mềm mở được road1 tại 20 phút 41 giây phẩy hai tư. Vì vậy, tìm được nguồn là kết quả của mô hình cùng chỉ mục và phần xử lý. Điểm cao vẫn cần kiểm tra bằng video.

Nguồn: Ca road1 của đề tài · Cơ sở mô hình: [1] Google DeepMind; [2] báo cáo EG2.
[1] https://huggingface.co/google/embeddinggemma-2
[2] https://arxiv.org/html/2610.37364v2

## 26. Bộ thử dùng để lựa chọn cấu hình
Trang 26 · Gợi ý 31 giây

Phép so sánh tiếp theo sử dụng bộ thử nghiên cứu phiên bản bảy: 70 video, 58 ảnh truy vấn khó và 276 khung lấy mẫu. Dữ liệu từ DAVIS 2017 được tổ chức lại cho bài toán truy hồi rồi bổ sung các video gây nhiễu. Kết quả phù hợp phải trùng video và đoạn trả về giao với nhãn đã nới biên nửa giây. Đây là một bộ thử riêng, không đồng nhất với ca road1 hay thư viện mười tệp của đợt đánh giá mới.

Nguồn: Kết quả nghiên cứu v7 của đề tài · Cấu hình và quy tắc đánh giá được ghi trong ghi chú.

## 27. Kiến trúc ứng dụng trên máy tính
Trang 27 · Gợi ý 31 giây

Giao diện React và TypeScript tiếp nhận ảnh, vùng cắt và phạm vi tìm. Python cùng FastAPI kiểm tra yêu cầu, điều phối EG2 rồi truy vấn chỉ mục. SQLite quản lý quan hệ giữa video, khung và thời điểm; ảnh xem trước và video lưu ở dạng tệp. API là giao diện lập trình ứng dụng, ở đây giao tiếp ngay trên máy. Tauri dùng mã Rust để tạo cửa sổ Windows và quản lý tiến trình Python. Nó không chạy thuật toán so ảnh.

Nguồn: Thiết kế thực tế: desktop/src và desktop/backend.

## 28. Lập chỉ mục từ video đến dữ liệu có thể tìm
Trang 28 · Gợi ý 32 giây

OpenCV đọc video theo lịch lấy mẫu; mốc thật do bộ giải mã trả về đi cùng ảnh. EG2 mã hóa từng lô thành vector 768 chiều và chương trình kiểm tra đầu ra. Dữ liệu khung, mã video, thời gian và vị trí tiếp tục được ghi theo lô. Vì vậy lần tìm sau có thể dùng lại vector, thay vì xử lý lại toàn bộ video. Nếu tệp nguồn hoặc cấu hình thay đổi, chương trình kiểm tra chữ ký chỉ mục trước khi sử dụng tiếp.

Nguồn: library.py · inference.py · store.py

## 29. Giao diện gửi gì và nhận gì?
Trang 29 · Gợi ý 39 giây

Khi người dùng bấm tìm, giao diện gửi ảnh truy vấn và phạm vi tìm đến API chạy trên chính máy tính.
Bộ xử lý Python dùng FastAPI nhận yêu cầu, kiểm tra dữ liệu rồi thực hiện tìm kiếm.
Tauri và Rust chủ yếu tạo cửa sổ ứng dụng và quản lý tiến trình; giao diện trao đổi trực tiếp với API cục bộ.
Kết quả trả về có mã video, gọi là video_id, và mốc thời gian, gọi là peak. Ví dụ, peak bằng 1.241,24 giây tương đương 20 phút 41,24 giây. Nhờ hai thông tin này, trình phát biết phải mở video nào và mở ở đâu.

## 30. Dừng giữa chừng vẫn biết làm tiếp từ đâu
Trang 30 · Gợi ý 39 giây

Một video dài có thể mất thời gian để chuẩn bị dữ liệu tìm kiếm. Vì vậy, FrameAtlas không đợi xử lý hết video mới lưu, mà chia khung hình thành từng nhóm nhỏ, gọi là các lô.
Sau khi xử lý xong một lô, chương trình lưu các vector và vị trí tiếp tục trong SQLite.
Nếu ứng dụng bị dừng khi đang làm dở, lần mở sau nó dựa vào mốc đã lưu để biết phần nào đã hoàn thành và phần nào còn thiếu. Phần chưa được xác nhận có thể được xử lý lại.Cách này giúp việc lập chỉ mục ổn định hơn, đặc biệt với video dài.
