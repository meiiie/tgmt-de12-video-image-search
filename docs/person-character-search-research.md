# Tìm người và nhân vật xuyên nhiều video: đánh giá sản phẩm

Ngày kiểm tra: 01/11/2026. Đây là nghiên cứu và phạm vi pilot, **chưa phải tính năng nhận diện đã triển khai hoặc benchmark chất lượng**. Chỉ agent chính thực hiện.

## Quyết định

Ưu tiên kiểm chứng **tìm các lần xuất hiện của nhân vật đã được người dùng chọn trong thư viện video của họ**, phục vụ tìm tư liệu và dựng clip. Đây là hướng có đầu ra rõ và dễ đối chiếu hơn việc tự chọn đoạn “hay nhất” hoặc chấm điểm nói: trả về đúng video, đúng đoạn, đúng đối tượng; người dựng duyệt và xuất phần cần dùng.

Mức ưu tiên này là nhận định về phạm vi kỹ thuật và khả năng kiểm chứng. Chưa có phỏng vấn editor, đo thời gian tiết kiệm hoặc xác nhận khách hàng trả tiền. Không đổi toàn bộ sản phẩm thành hệ thống nhận diện chỉ vì thêm một ý tưởng mới.

## Nhu cầu và cạnh tranh có bằng chứng

- Người dùng Immich yêu cầu tìm người ở các thời điểm bên trong video, vì ảnh đại diện có thể không chứa người cần tìm. Thảo luận còn đề xuất lưu timestamp và gộp các lần xuất hiện: [discussion #5936](https://github.com/immich-app/immich/discussions/5936). Đây là nhu cầu được phát biểu trực tiếp, chưa phải khảo sát đại diện.
- [FAQ Immich](https://docs.immich.app/FAQ/) tại thời điểm đọc nói ML chạy trên thumbnail và quét toàn video còn là khả năng tương lai. [Tài liệu nhận diện](https://docs.immich.app/features/facial-recognition/) mô tả tách phát hiện mặt, embedding mặt và gom nhóm. Không suy diễn tình trạng của mọi nhánh phát triển từ FAQ.
- [immich-moments](https://github.com/immich-app/immich/discussions/31625) đã kết hợp cảnh, người và lời thoại để tìm tới timestamp. Tác giả tự ghi nhận thư viện thử chủ yếu là phim ngắn/clip tổng hợp, chưa biết chất lượng trên video gia đình dài. Không sử dụng tốc độ tác giả nêu làm số liệu của FrameAtlas.
- [Fennec Search](https://github.com/JasonMakes801/fennec-search) công bố tìm lời thoại, cảnh và khuôn mặt trong thư viện local. Đây là tham khảo kiến trúc, chưa được chạy hoặc kiểm định trong workspace này.
- [DaVinci Resolve Studio](https://www.blackmagicdesign.com/products/davinciresolve/edit) đã có phân tích khuôn mặt và tự tạo bin theo người. Vì vậy “AI tìm người” không phải tính năng mới đủ để đảm bảo một sản phẩm riêng đáng dùng.

Giả thuyết giá trị cần thử: một app desktop tìm tới **đoạn cụ thể xuyên nhiều thư mục/dự án**, kết hợp nhân vật với bối cảnh/lời thoại, sửa kết quả dễ và đưa đoạn đã chọn vào quy trình dựng. So trực tiếp với công cụ người dùng đã có; nếu họ làm nhanh hơn bằng Resolve hoặc công cụ lưu trữ hiện tại, không nên xây bản thay thế chỉ vì có model.

## Các bài toán khác nhau

| Yêu cầu | Điều phải xác định | Vai trò hợp lý của EG2 |
|---|---|---|
| “Người mặc áo đỏ” | Đặc điểm nhìn thấy; có thể khớp nhiều người | Truy hồi ngữ nghĩa/ảnh làm baseline |
| “Tìm những cảnh giống ảnh nhân vật này” | Vùng hình ảnh gần mẫu | EG2 trên crop là baseline cần đo, không xác nhận danh tính |
| “Cùng người A trong nhiều video” | Tính nhất quán giữa góc mặt, cảnh, trang phục | Model nhận diện mặt/ReID chuyên biệt cùng bộ ảnh mẫu; EG2 tìm bối cảnh |
| “A đang nói về pin” | Xuất hiện, người nói và nội dung có quan hệ với nhau | EG2 tìm chủ đề; cần transcript, timestamp và kiểm chứng người nói |
| “Nhân vật hoạt hình/game A” | Thiết kế nhân vật, skin, tên trong game, quan hệ với người điều khiển | Crop/embedding thị giác, tracking và OCR tùy dữ liệu; face model người không thay thế được |

Một người xuất hiện trên hình không đồng nghĩa họ đang nói. Nhắc tên A trong lời thoại không chứng minh A có mặt. Cùng diễn viên có thể đóng hai nhân vật; cùng avatar có thể được hai người điều khiển. Các quan hệ này phải được lưu và hiển thị riêng, không tự hợp nhất thành một nhãn “người”.

[Model card EG2](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2) công bố embedding đa phương thức cho retrieval/classification/clustering. Các điểm benchmark tổng hợp được đọc không đủ chứng minh khả năng nhận diện cùng người trên thư viện đích. Không kết luận EG2 hoàn toàn không thể học identity; chỉ chưa có bằng chứng để dùng nó làm bộ xác nhận identity duy nhất.

[Nghiên cứu LTCC](https://arxiv.org/abs/2005.12633) chỉ rõ việc đổi trang phục là một thách thức riêng của ReID. [TransReID](https://github.com/damo-cv/TransReID) là nguồn tham khảo chuyên nhiệm vụ, không phải bằng chứng chất lượng trên video của người dùng.

## Trường hợp sản phẩm nên thử trước

Editor có nhiều file phỏng vấn hoặc sự kiện với một nhóm nhân vật lặp lại. Họ chọn vài ảnh mẫu từ tư liệu, đặt tên trong dự án và yêu cầu gom các đoạn có nhân vật đó để dựng.

Luồng đề xuất:

1. Chọn thư mục video và các ảnh mẫu của nhân vật A; chỉ định phạm vi dự án.
2. App trả các khoảng xuất hiện theo video, thumbnail có vùng đánh dấu và nút nhảy tới thời điểm nguồn.
3. Người dùng xác nhận hoặc loại kết quả; thao tác sửa có thể hoàn tác.
4. Lọc tiếp theo cảnh hoặc chủ đề, duyệt đầu/cuối đoạn rồi xuất clip hoặc danh sách dựng.

Ưu tiên tư liệu có mặt tương đối rõ và nhóm nhân vật giới hạn. Các trường hợp quay xa, sau lưng hoặc đổi trang phục là nhóm kiểm tra khó; trả “chưa đủ bằng chứng” khi cần. Không tự gán tên người lạ; tên là nhãn người dùng đặt cho thư viện.

Phạm vi này giữ EG2 ở đúng công việc có ích: “A ở ngoài trời”, “A trong cảnh trao quà” hoặc tìm cảnh gần ảnh tham chiếu. Khả năng tìm “A đang giải thích vấn đề X” cần bổ sung transcript và liên kết người nói, chưa thuộc tính năng hiện có.

## Video Goose Goose Duck hiện có có phù hợp không?

Có thể dùng làm bài thử **nhân vật game**, nhưng phải tách các mục tiêu:

- Tìm một avatar/skin nhìn thấy được là truy hồi đối tượng; màu áo một mình chưa chứng minh cùng nhân vật.
- Tên hiển thị có thể là tín hiệu OCR, cần giữ phạm vi trận/phiên và xác nhận quan hệ với avatar.
- Tìm người đang nói cần xử lý lời thoại/người nói; không suy ra từ avatar đang ở giữa màn hình.
- Webcam của streamer nếu xuất hiện xuyên suốt sẽ làm tìm người đó ít hữu ích: gần như mọi đoạn đều khớp. Phải đo giá trị của kết quả đối với tác vụ dựng, không chỉ đếm số hit.

Một video dài cắt thành nhiều file chỉ kiểm tra thao tác tìm xuyên file. Nó không kiểm chứng khả năng nhận ra cùng người/nhân vật trong nhiều buổi quay, góc máy hoặc điều kiện khác nhau.

[Nghiên cứu Character-Centric Understanding of Animated Movies](https://www.robots.ox.ac.uk/~vgg/research/animated_ad/) xây kho mẫu nhân vật đa phương thức vì ngoại hình/biến dạng của hoạt hình khác nhận diện mặt người. Đây là bằng chứng cần phân biệt domain, không phải benchmark Goose Goose Duck.

Với bóng đá, đồng phục và khuôn mặt nhỏ khiến cần thêm số áo, đội và tracking. [SoccerNet-GSR](https://www.soccer-net.org/tasks/game-state-reconstruction) định nghĩa chính các thành phần này; [baseline](https://github.com/SoccerNet/sn-gamestate/) kết hợp detection, ReID, tracking, jersey recognition và team affiliation. Do đó chưa chọn bóng đá làm pilot identity đầu tiên.

## Khoảng cách với code hiện tại

Đã đọc `desktop/backend/inference.py`, `library.py` và `store.py`:

- `Encoder.images()` encode ảnh RGB được cung cấp; worker hiện truyền toàn khung hình.
- `Library.search()` so vector với các frame, có thể tìm xuyên video và trả khoảng thời gian.
- Database hiện có `videos`, `frames`, `moments`; chưa có detections, tracklets, bộ ảnh mẫu hoặc quyết định xác nhận nhân vật.

Vì vậy tìm bằng ảnh hiện có là nền để tạo ứng viên, **chưa phải tính năng “tìm mọi lần người A xuất hiện”**. Kết quả DAVIS và lab audio trước đó không thay thế đánh giá identity.

Phần bổ sung tối thiểu nếu pilot được thực hiện:

1. Lấy frame/cảnh với timestamp thật; phát hiện vùng đối tượng thích hợp với domain.
2. Giữ các lần xuất hiện liên tục trong từng cảnh; không mặc định track ID cục bộ có cùng nghĩa xuyên các video.
3. So mẫu trên crop bằng encoder phù hợp, giữ ứng viên chưa rõ và bằng chứng nguồn. Gom đoạn nhưng không kéo một hit đơn lẻ thành khẳng định xuất hiện suốt khoảng trống.
4. Cho người dùng sửa nhóm và duyệt timeline; dùng EG2 riêng để lọc bối cảnh. Không cộng tùy tiện cosine khuôn mặt, cosine EG2 và điểm detector thành một “% đúng”.

Chưa chọn model nhận diện để đóng gói. [InsightFace](https://github.com/deepinsight/insightface) ghi mã MIT nhưng nhiều model/data phát hành chỉ dùng nghiên cứu phi thương mại và có quy trình xin license riêng. Apache-2.0 của EG2 không cấp quyền cho trọng số thành phần khác. Cần kiểm tra đúng artifact được chọn trước khi đưa vào bản sản phẩm.

## Pilot và điều kiện quyết định

Đây là kế hoạch, **chưa chạy và chưa có số chất lượng**:

- Một tập tư liệu nhiều file thực sự, với nhãn nhân vật và khoảng xuất hiện do chủ tư liệu/editor xác nhận. Tách query/reference với video đánh giá; không dùng cùng frame hoặc bản sao gần nhau làm bằng chứng tổng quát hóa.
- Có người không xuất hiện trong gallery, người giống nhau/áo giống nhau, mặt nghiêng/che, thay cảnh, đổi đồ; đánh dấu trường hợp không thể xác định từ hình.
- So baseline EG2 toàn frame, EG2 crop và hệ chuyên nhiệm vụ trên cùng dữ liệu. Thử nhận diện mặt người riêng với avatar; không gộp điểm hai domain.
- Đo precision của đoạn gợi ý, recall các lần xuất hiện, độ lệch đầu/cuối đoạn, tỷ lệ phải sửa và thời gian hoàn thành tác vụ. Báo cả chi phí lập chỉ mục lần đầu, dung lượng và độ trễ tìm sau đó.
- Đánh giá tác vụ “tìm đủ cảnh A để dựng một đoạn cụ thể” so với tua tay/công cụ hiện tại. Không dùng FPS model hoặc top-1 của một ảnh để kết luận đã giải quyết nhu cầu editor.
- Nếu chỉ đúng trong cùng outfit/cảnh, giữ tuyên bố ở phạm vi đó. Nếu thời gian sửa kết quả lớn hơn lợi ích, thu hẹp về tìm ứng viên theo ngoại hình thay vì mở rộng thêm tính năng nhận diện.

## Nguồn và phạm vi thực hiện

Đã dùng 5 truy vấn Exa theo các hướng nhu cầu/cạnh tranh, ReID, bóng đá, công cụ dựng và nhân vật hoạt hình (25 vị trí kết quả, có trùng), cùng lượt web tìm tài liệu chính chủ ban đầu. Đọc các trang gốc được dẫn trên. Fetch repo immich-moments bị lỗi; dùng bài giới thiệu do tác giả đăng trong Immich, không coi là đã audit code dự án đó.

Lượt này hoàn thành đối chiếu sản phẩm, đọc luồng index/search đang có và xác định pilot. Không có thí nghiệm nhận diện người trên video thật, chưa bổ sung detector/tracker vào app, chưa có bằng chứng về thị trường hay độ chính xác identity của FrameAtlas.
