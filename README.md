# UniGuideBot — Chọn trường, hiểu nghề

Ứng dụng Python/SQLite, giao diện sáng/tối, ưu tiên Bắc Bộ. Bốn không gian: Tư vấn AI, Hồ sơ của tôi, Xu hướng nghề, Danh mục trường.

## Chạy trong VS Code

```powershell
python portable_server.py
```

Mở http://127.0.0.1:5001. Bản portable dùng thư viện chuẩn. Trong phiên debug hiện có, Ctrl+Shift+F5 để nạp mã mới; sau đó tải lại trang. Không chạy hai máy chủ trên cùng cổng.

Flask tùy chọn: cài `requirements.txt`, chạy `python app.py`. Cả hai máy chủ dùng chung service, dữ liệu, hồ sơ và bộ cập nhật xu hướng. Triển khai Flask chỉ dùng một tiến trình cho tác vụ nền trong phiên bản này.

## AI và tra cứu web

- `.env` chỉ được đọc tại máy chủ. Cấu hình `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_GROUNDING_MODEL`; thay cấu hình rồi khởi động lại máy chủ. Tệp `.env.example` chỉ có giá trị giữ chỗ.
- Mọi phản hồi chat và tư vấn hồ sơ đều gọi Gemini; khi AI lỗi, trả lỗi có thể thử lại, không thay bằng câu trả lời theo mẫu. Đã bỏ bảng/nút kiểm tra kết nối và nhãn dữ liệu cục bộ.
- Ngày 27/10/2026, mô hình `gemini-3.5-flash-lite` đã trả lời thành công trong kiểm tra trực tiếp. Google Search vẫn trả 429 riêng. Lỗi này không đủ chứng minh người dùng đã tiêu hết hạn mức; hạn mức phụ thuộc dự án, mô hình và dịch vụ.
- Câu hỏi cần thông tin mới thử Google Search. Chỉ nhận `grounded=true` khi có nguồn và bằng chứng trích dẫn. Nếu Search lỗi nhưng AI thường hoạt động, AI tiếp tục tư vấn với hồ sơ/danh mục và tiêu đề RSS hiện có, nêu rõ chưa tra cứu Google thành công. Không suy ra số liệu thị trường từ tiêu đề.
- Không lưu khóa trong HTML/JS; không tự gọi API kiểm tra kết nối từ giao diện.

## Danh mục trường miền Bắc

134 bản ghi tổng cộng, trong đó 127 tại Bắc Bộ, 26 thuộc nhóm ngoài công lập (gồm tư thục và cơ sở có vốn đầu tư nước ngoài). Số bản ghi bao gồm đại học hệ thống, trường/học viện, trường thành viên và một số cơ sở/phân hiệu có nhãn riêng; không đồng nghĩa 127 pháp nhân độc lập.

Tên/mã/website được đối chiếu cổng tuyển sinh Bộ GDĐT và chỉ mục khu vực; các trường hợp phân loại thiếu dấu được kiểm tra thêm nguồn trường. Xem `sql/catalogue-audit.json` cho phạm vi và hạn chế. Không tuyên bố bao phủ 100% các đơn vị mới/đổi tên/sáp nhập. Loại hình và địa điểm là thông tin danh mục; tên địa điểm cũ được giữ ở một số cơ sở để dễ tìm. Thanh Hóa không được phân loại vào Bắc Bộ.

Mỗi bản ghi tách **mã ứng dụng** với **mã tuyển sinh**. Ví dụ Luật Hà Nội giữ mã ứng dụng cũ HLU nhưng mã tuyển sinh LPH; Hạ Long có mã tuyển sinh HLU và mã ứng dụng HALONG. Tránh dùng mã ứng dụng thay mã đăng ký xét tuyển.

12 nhóm lĩnh vực tham khảo. Một số trường chưa phân loại nhóm ngành; không tự gán ngành cho mọi trường. Gợi ý hồ sơ chỉ dùng các trường có lĩnh vực khớp; vì vậy danh sách gợi ý không bao phủ mọi trường. Số liệu học phí/điểm chuẩn có nguồn được lưu riêng tại `sql/admissions.json`. Không bảo đảm đỗ, vừa ngân sách hoặc có việc làm.

`init_db()` bổ sung bản ghi mới và đồng bộ metadata danh mục vào DB hiện có, không xóa bảng hay ghi đè mô tả người dùng đã sửa. Không xóa DB để cập nhật. Sao lưu trước khi đồng bộ. Thay đổi nhóm ngành có tính chất bổ sung; xóa/sửa phân loại cũ cần migration được kiểm tra riêng.

## Hồ sơ cá nhân

Nhập sở thích, thế mạnh, môn/kỹ năng, điểm/phương thức, ngân sách, khu vực, nhóm ngành và mục tiêu. Hồ sơ lưu trong localStorage của trình duyệt; có nút xóa. Mỗi địa chỉ/cổng trình duyệt có kho riêng.

Khi yêu cầu tư vấn hoặc chọn “Dùng hồ sơ đã lưu”, các mục hồ sơ được gửi đến máy chủ rồi đến Gemini để phân tích. Máy chủ không lưu hồ sơ hoặc câu hỏi vào DB/cache xu hướng. Không có đăng nhập hay đồng bộ nhiều thiết bị. Không cần nhập tên, liên hệ hoặc thông tin định danh.

AI nhận các trường và lý do khớp hồ sơ làm ngữ cảnh, đồng thời xây dựng lộ trình 90 ngày. Điểm/ngân sách không tự xác nhận đủ điều kiện. Nút Xuất PDF chạy ngay trên trình duyệt, nhúng phông Noto Sans để giữ dấu tiếng Việt; chỉ kèm lộ trình khi đã nhận tư vấn AI.

## Tab xu hướng

- Bộ thu thập chạy ở máy chủ, cả khi đóng tab, miễn ứng dụng còn chạy. Mỗi 2 giờ tính từ lượt lưu thành công; khi khởi động sẽ kiểm tra bản lưu có quá hạn không.
- Lấy tiêu đề, liên kết và ngày đăng từ RSS công khai VnExpress/Tuổi Trẻ; lọc nội dung nghề nghiệp/ngành học/kỹ năng/tuyển sinh. Không lưu toàn bộ bài báo. Ngày đăng và giờ thu thập tách riêng.
- Phân tích thị trường bằng Gemini + Google Search, có nguồn và mốc thời gian dữ liệu. Tin RSS vẫn cập nhật khi Gemini hết hạn mức. Không gắn nhãn phân tích AI cho tin RSS.
- SQLite lưu bản tin công khai; giữ bản cũ khi lỗi và hiển thị thời gian thật. Không đổi timestamp phân tích AI khi chỉ RSS thành công.
- Có nút cập nhật ngay; khóa chống chạy trùng và tối thiểu 60 giây giữa các lượt. Lỗi toàn bộ sẽ thử lại sau 10 phút. Khi dừng ứng dụng thì việc cập nhật cũng dừng; đây không phải dịch vụ hoạt động 24/7.

## Lịch sử chat trên máy

Hội thoại lưu trong localStorage với khóa `uniguide-chats-v1`. Có danh sách lịch sử, mở lại, trò chuyện mới và xóa từng cuộc. Tải lại trang sẽ khôi phục cuộc đang mở. Gửi tối đa 16 tin nhắn trước đó (18.000 ký tự) làm ngữ cảnh AI. Hội thoại không lưu vào SQLite. Dữ liệu tách theo trình duyệt và địa chỉ/cổng; xóa dữ liệu trình duyệt sẽ mất lịch sử. Không thêm tác vụ khởi động Windows.

## Học phí, điểm chuẩn và giao diện

Nút Học phí & điểm chuẩn mở bảng theo năm 2024/2025/2026, có tìm ngành, phương thức, thang điểm và liên kết nguồn. Hiện có 274 dòng điểm chuẩn và 27 dòng học phí thuộc UET, PTIT, HUST, ULIS và HPN (HPN mới có học phí 2026); chưa bao phủ mọi trường trong danh mục. Năm thiếu nguồn để trống. Phân biệt học phí/năm, học kỳ, tín chỉ; không tự quy đổi thiếu căn cứ.

Tin RSS có ảnh thu nhỏ lấy từ feed, tải lười và có nền thay thế khi ảnh lỗi. Giao diện sáng/tối, chuyển động nhẹ, hỗ trợ giảm chuyển động và màn hình nhỏ. Thẻ trường thu gọn khoảng đệm, logo; chat mặc định hiển thị 4 thẻ, có mục mở rộng.

## Kiểm thử

```powershell
python -m unittest test_system test_features
```

44 bài kiểm thử dùng DB tạm và provider giả lập, chặn lời gọi mạng ngoài dự kiến: câu ngoài chủ đề, luôn dùng AI, lỗi provider, lịch sử/ngữ cảnh, danh mục Bắc Bộ, hồ sơ, grounding, 429, RSS và dữ liệu tuyển sinh theo năm/đơn vị. Đã kiểm tra AI thật trên giao diện, phục hồi hội thoại ở tab mới và xuất/render PDF tiếng Việt. Google Search của tài khoản hiện tại chưa xác minh thành công.

## API

- `POST /chat`: message, filters, profile, history tùy chọn.
- `POST /api/recommend`: profile, use_web.
- `GET /api/universities?region=bac&field=cntt`: danh mục đầy đủ để lọc trên giao diện.
- `GET /api/stats`: tổng số cơ sở, lĩnh vực, miền, cơ sở miền Bắc và ngoài công lập miền Bắc.
- `GET /api/trends`, `POST /api/trends/refresh`: bản lưu công khai và yêu cầu cập nhật nền.
- `GET /api/admissions?code=HUST`, `POST /api/admissions/lookup`: dữ liệu tuyển sinh có nguồn và tra cứu web.
- `GET /api/ai/status`: trạng thái lần gọi gần nhất, không chứa khóa; không có nút kiểm tra kết nối.

Giới hạn body 96 KB; câu hỏi 1–2.000 ký tự; từng mục hồ sơ có giới hạn riêng. Máy chủ bind localhost. Không dùng trực tiếp như hệ thống nhiều người dùng công khai: chưa có tài khoản, phân quyền hay hạn mức theo người dùng.

## Bản phát hành Vercel

Đã chuẩn bị dự án `uniguidebot` trong team `viet-longs-projects`. Nguồn sạch được đóng gói riêng, không gồm `.env`, DB local, tài liệu riêng hoặc backup. Kho nguồn riêng tư: https://github.com/long7102/UniGuideBot. Kết nối nhánh main với Vercel để tự triển khai khi đẩy mã. Đã lưu khóa Gemini trong cấu hình mã hóa phía máy chủ của Vercel theo phép của chủ dự án; khóa không nằm trong Git. Build command `python build_assets.py` đồng bộ tài nguyên giao diện sang thư mục CDN public/static.

Trên Vercel, danh mục SQLite được khởi tạo từ JSON công khai trong `/tmp`. Tin RSS được kiểm tra đồng bộ khi có yêu cầu và bản lưu quá 2 giờ; không chạy thread nền thường trực. Cache `/tmp` có thể mất khi đổi instance, chưa phải kho dữ liệu dùng chung bền vững. Chat và hồ sơ vẫn ở trình duyệt, tách theo tên miền. Giới hạn gọi AI theo IP trong từng tiến trình (8/phút), không phải giới hạn chung nhiều instance.

Câu hỏi về địa điểm, số cơ sở, chương trình đào tạo và nội dung nghề nghiệp thuộc phạm vi giáo dục. Dữ kiện cơ sở HPN được đối chiếu từ thông báo tuyển sinh 21/5/2026; phân biệt ba địa điểm với hai mã tuyển sinh.
