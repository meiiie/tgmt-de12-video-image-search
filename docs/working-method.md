# Cách làm việc cho Đề 12

Ngày khảo sát: 01/11/2026, Asia/Saigon. Quy tắc bắt buộc nằm trong [AGENTS.md](../AGENTS.md).

## Một agent thực hiện toàn bộ

Agent chính tự đọc, phân tích, sửa và kiểm chứng. Không dùng subagent, không giao việc qua chat khác. Những bước phân công trong pstack được thay bằng các lượt tự kiểm tra theo từng phần.

## Luồng thực hiện

1. Xác định đầu vào, đầu ra và điều kiện hoàn tất của phần việc. Với bài này, ảnh truy vấn phải trả đúng video và khoảng thời gian, không chỉ một điểm cosine cao.
2. Đọc điểm vào và đường gọi liên quan. Dùng [bản đồ logic](logic-review.md) khi cần định vị code; không bắt đọc toàn bộ nghiên cứu cho mỗi chỉnh sửa nhỏ.
3. Lưu mốc trước thay đổi. Ghi commit, môi trường, model, dữ liệu, cách chia tập và câu lệnh.
4. Tái hiện vấn đề bằng trường hợp nhỏ. Sau đó sửa nguyên nhân trong đúng phạm vi; giữ nguyên benchmark và tham số không liên quan.
5. Chạy kiểm tra phù hợp rồi chạy qua CLI hoặc app khi thay đổi ảnh hưởng luồng người dùng.
6. Báo rõ phần đã chạy, kết quả, giới hạn và việc còn lại. Không gọi kiểm tra cú pháp hoặc dữ liệu tổng hợp là đánh giá độ chính xác.

Mỗi thí nghiệm cần có giả thuyết và một điều kiện giữ hoặc bỏ thay đổi. Không đổi model, sampling, metric và dữ liệu cùng một lần rồi quy toàn bộ chênh lệch cho model.

## Điều học từ Neko Aurora

Đã đối chiếu checkout Neko Aurora tại commit `66376d68691d8bce16b6565c6268c4331802ef57`, cùng các chat liên quan do người dùng yêu cầu đọc. GitHub main hiện ở `35dfbe46b79d25bb6df780befbd345938f643aef`; đã đọc lại AGENTS và CONTRIBUTING tại mốc remote này, nội dung quy tắc được tham khảo không đổi.

- Giữ bản đồ trách nhiệm theo module, như Neko tách UI, host và runtime. Ở đây là sampling, embedding, retrieval, temporal localization, evaluation và UI.
- Ghi exact commit, lệnh, môi trường và PASS/FAIL/BLOCKED. Tách bằng chứng fixture khỏi thử nghiệm dữ liệu thật.
- Giữ thay đổi tập trung và lưu bằng chứng để tiếp tục phiên sau.
- Dùng môi trường và dữ liệu local riêng; không đưa cache, trạng thái tài khoản hay token vào Git.

Nguồn repo: [AGENTS.md](https://github.com/meiiie/neko-aurora/blob/66376d68691d8bce16b6565c6268c4331802ef57/AGENTS.md), [CONTRIBUTING.md](https://github.com/meiiie/neko-aurora/blob/66376d68691d8bce16b6565c6268c4331802ef57/CONTRIBUTING.md).

Các lựa chọn Go, Rust, Tauri, Railway và cấu trúc quyền của Neko thuộc dự án đó. Bài Python này không cần sao chép chúng. Yêu cầu deploy ở chat cũ không phải yêu cầu deploy repo hiện tại.

## Cách dùng pstack và skill

- `karpathy-guidelines` dùng cho code: nêu giả định, sửa đúng chỗ, ưu tiên lời giải đơn giản và kiểm chứng được.
- Dùng ý tưởng Investigation của pstack để giải thích code bằng bằng chứng. Với lỗi đã tái hiện, chuyển sang chu trình sửa và kiểm tra.
- Chỉ đọc skill liên quan đến tác vụ đang làm. `find-skills` dùng khi thật sự thiếu khả năng; chưa cần cài thêm skill cho bước khảo sát này.
- `skill-creator` chỉ cần khi tạo hoặc sửa skill. Phiên này không sửa skill cá nhân.
- Bản pstack local có `harness-zcode.md` và vai trò `inherit-parent`. Đây là cấu hình ZCode, không phải cấu hình Codex đã xác minh. Không chép tên tool hoặc model slug sang Codex.
- Bất kỳ bước subagent nào trong skill đều bị quy tắc của người dùng loại bỏ.

## Đối chiếu hai tài liệu

[Anthropic: How Claude Code works in large codebases](https://claude.com/resources/articles/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) nhấn mạnh context gọn và phân tầng, skill nạp khi cần, và kiểm tra tự động có thể chạy lại. Áp dụng ở đây bằng AGENTS ngắn, bản đồ code riêng và script tái hiện. Khuyến nghị subagent trong bài không áp dụng theo yêu cầu người dùng.

[OpenAI: Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) cảnh báo trigger skill quá rộng, chỉ dẫn chồng chéo và quy trình quá cứng. Áp dụng ở đây bằng việc nêu kết quả cần đạt, đọc theo phạm vi, và không tự cài toàn bộ workflow chỉ vì có sẵn skill.

## Điều kiện hoàn tất cho các bước tiếp theo

| Phần việc | Bằng chứng cần có |
|---|---|
| Sửa temporal retrieval | Ca tái hiện trước sửa thất bại; sau sửa đạt; thứ tự video không làm đổi top-1 |
| Đổi backbone hoặc preprocessing | Cùng dataset/split/query; index và query cùng model/precision; số liệu mới và cấu hình đầy đủ |
| Tăng tốc | Cùng điều kiện đo, phân biệt tải model với chạy nóng, embed với search; báo ảnh hưởng độ chính xác |
| Đổi cách gộp đoạn | Đo cả tìm đúng video, peak và IoU; kiểm tra nhiều miền nếu muốn đổi mặc định |
| Thay UI | Chạy thật luồng truy vấn, kiểm tra kết quả và thông báo lỗi |

Mốc hiện tại được ghi trong [baseline local](../notes/local-baseline-2026-11-01.md).
