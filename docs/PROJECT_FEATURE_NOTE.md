# Bảng giới thiệu dự án và tính năng

Tài liệu này giúp quản lý, nhân viên Content, IT/Ads Operator hoặc người mới hình dung sản phẩm mà không cần đọc code.

## 1. Thuyết minh ngắn

**Facebook Ads Khải Hoàn** là bàn lập kế hoạch và kiểm duyệt quảng cáo nội bộ. Thay vì nhân viên phải tự đi qua ba tầng phức tạp của Ads Manager cho từng bài, họ đưa các bài Facebook có sẵn vào một màn hình, chọn nhiều bài cho cùng một cách chạy, xây dựng các nhánh phễu và gửi toàn bộ cây kế hoạch cho người duyệt. Sau khi duyệt, backend gọi Meta Marketing API để tạo cấu trúc quảng cáo ở trạng thái tạm dừng. Con người vẫn là người kiểm tra và bật chạy cuối cùng.

## 2. Bức tranh sản phẩm

| Thành phần | Mô tả dễ hình dung | Giá trị mang lại |
|---|---|---|
| Kho bài Page | Lọc bài theo từ ngày–đến ngày hoặc dán link thủ công | Không cần tìm/copy từng bài qua nhiều tab |
| Thẻ creative | Hiện hình, nội dung rút gọn, loại media ngay cạnh link | Biết đang chọn bài nào, giảm nhầm creative |
| Bộ chọn nhiều bài | Chọn một hoặc nhiều link trước khi cấu hình | Một thao tác áp dụng cho cả nhóm bài |
| Flow quảng cáo | Một “công thức chạy” gồm mục tiêu, ad set, audience, budget, placement | Chuẩn hóa quyết định và tái sử dụng nghiệp vụ |
| Nhiều flow | Một bài có thể được chạy ở nhiều tầng/cách khác nhau | Hỗ trợ test phễu mà không nhập bài lại |
| Gom nhóm | Các ads cùng cấu hình nằm chung campaign/ad set | Cấu trúc gọn, dễ xem ngân sách và tối ưu |
| Campaign đích | Chọn tạo mới hoặc chiến dịch Meta có sẵn phù hợp | Không tạo tràn lan campaign, tận dụng cấu trúc đang dùng |
| Thư viện đối tượng | Broad, Custom, Lookalike; kiểm soát, gợi ý, loại trừ | Nhân viên chọn theo giao diện gần Meta nhưng dễ hiểu hơn |
| Tệp Meta | Đọc tệp đã có; tạo Page Engagers/Page Messagers và lưu preset | Tệp tạo một lần, dùng lại trong Planner |
| Thư viện placement | Thiết bị, nền tảng, feed/reels/search theo preset | Giảm sai vị trí quảng cáo và thao tác lặp |
| Ngân sách/lịch | Ngân sách ngày hoặc trọn đời, giờ bắt đầu/kết thúc, tiền tệ ad account | Tránh nhầm đơn vị và thiếu lịch bắt buộc |
| Cây duyệt | Campaign → Ad set → Ads giống tư duy Ads Manager | IT nhìn tổng thể trước khi đẩy lên Meta |
| Publish an toàn | Chỉ người duyệt được tạo; mọi tài sản là `PAUSED` | Không có quảng cáo tự chạy ngoài ý muốn |
| Retry/ledger | Nhớ ID đã tạo và tiếp tục từ phần lỗi | Không nhân đôi campaign/ad set/ad khi mạng lỗi |
| Bảng xử lý lỗi | Gom ads lỗi, chờ duyệt, tạm dừng; link mở Ads Manager | Con người chỉ tập trung vào mục cần sửa |
| CSV/Notion dự phòng | Luồng xuất bulk CSV cũ vẫn hoạt động | Có đường lui trong giai đoạn chuyển sang API |

## 3. Hành trình của một kế hoạch

| Bước | Người thao tác | Việc nhìn thấy/làm | Kết quả |
|---:|---|---|---|
| 1 | Content | Chọn khoảng ngày hoặc dán nhiều link | Danh sách bài cần quảng cáo |
| 2 | Content | Xem preview và tick các bài cùng cách chạy | Tập creative của flow hiện tại |
| 3 | Content | Chọn mục tiêu → vị trí chuyển đổi → mục tiêu hiệu quả | Khung campaign/ad set đúng nghiệp vụ |
| 4 | Content | Chọn audience, budget, lịch, placement | Flow hoàn chỉnh |
| 5 | Content | Lặp lại nếu cần cách chạy/tầng phễu khác | Một plan có nhiều flow rõ ràng |
| 6 | Content | Xem preview cây và gửi duyệt | Snapshot `PENDING_REVIEW` |
| 7 | IT/Ads Operator | Đăng nhập, kiểm tra cây, ghi chú | `APPROVED` hoặc `REJECTED` |
| 8 | IT/Ads Operator | Bấm publish sau khi đã duyệt | Meta objects `PAUSED`; kết quả full/partial |
| 9 | IT/Ads Operator | Mở bảng vấn đề/Ads Manager | Sửa đúng ads lỗi, kiểm tra lần cuối |
| 10 | Người có quyền | Chủ động bật quảng cáo đạt yêu cầu | Chiến dịch bắt đầu phân phối |

## 4. Ví dụ nghiệp vụ nhiều bài

Giả sử có ba bài A, B, C:

| Flow | Bài được chọn | Cấu hình | Cách gom mong đợi |
|---|---|---|---|
| F1 — lạnh/video | A, B | Awareness/Engagement, ThruPlay, nữ Phan Thiết, mobile Facebook Reels/Feed | 1 campaign + 1 ad set + 2 ads |
| F2 — ấm/tin nhắn | A, B, C | Messages, người tương tác Page, loại người đã nhắn | 1 campaign + 1 ad set + 3 ads |
| F3 — remarketing | C | Messages/Sales phù hợp, khách đã nhắn còn phân vân | 1 campaign + 1 ad set + 1 ad |

Bài A và B không cần nhập lại khi chuyển từ F1 sang F2. Tool chỉ tạo flow mới và giữ cấu trúc trực quan.

## 5. Điều hệ thống tự động và không tự động

| Hệ thống có thể làm | Hệ thống cố ý không tự làm |
|---|---|
| Đọc bài/creative khi Meta cho phép | Không lấy dữ liệu bằng cách điều khiển Chrome hoặc scraping đăng nhập cá nhân |
| Validate và nhóm plan | Không đoán silently khi thiếu cấu hình quan trọng |
| Đọc campaign/audience thuộc quyền token | Không truy cập BM/ad account/Page chưa được gán quyền |
| Tạo campaign/ad set/ad `PAUSED` | Không tự bật chạy |
| Tạo một số Custom Audience đã hỗ trợ | Không tự tạo mọi loại audience của Meta |
| Báo lỗi từng ad và retry phần thiếu | Không tự xóa tài sản thật hoặc sửa lỗi chính sách |
| Đề xuất AI trong phiên bản tương lai | Không cho AI tự publish vượt bước người duyệt |

## 6. An toàn và trách nhiệm

| Rủi ro | Lớp bảo vệ |
|---|---|
| Lộ token Meta | Token chỉ ở backend `.env`, không gửi xuống browser |
| Nhân viên bấm nhầm publish | Publish yêu cầu phiên approver và CSRF |
| Quảng cáo chạy ngay | Tất cả object tạo ở `PAUSED` |
| Retry tạo trùng | Publish ledger lưu từng Meta ID |
| Một ad lỗi làm hỏng cả batch | Kết quả partial; tiếp tục các ad độc lập |
| Chọn campaign sai mục tiêu | Lọc ở UI và validate lại ở backend |
| Chồng lấn tệp phễu | Preset và quy tắc exclusion theo tầng |
| Mở tool công khai | Chỉ LAN tin cậy; muốn Internet phải có HTTPS + authentication/reverse proxy |

## 7. Trạng thái tính năng

| Trạng thái | Hạng mục |
|---|---|
| Đã có | Planner nhiều link/một flow; preview creative; import bài theo ngày; xóa link; nhiều flow |
| Đã có | Campaign mới/có sẵn; budget/lịch; audience/placement presets |
| Đã có | Review tree; approver session; CSRF; Meta publish `PAUSED`; ledger; partial retry |
| Đã có | Đọc/tạo Page engagement/message Custom Audience và lưu preset |
| Đã có | Bảng ads lỗi/chờ duyệt/tạm dừng và link Ads Manager |
| Dự phòng | Notion draft, Facebook bulk CSV, Supabase dashboard |
| Đang hoàn thiện | Mở rộng mapping ad set mẫu và regression trên nhiều objective/tài khoản |
| Chưa production | AI đọc creative và tự gợi ý plan bằng OpenAI API |
| Chưa có | Authentication riêng cho từng nhân viên và triển khai Internet công khai hoàn chỉnh |

## 8. Chỉ số nên theo dõi

| Nhóm chỉ số | Gợi ý đo |
|---|---|
| Tốc độ vận hành | Thời gian từ nhập 10 bài đến gửi duyệt; số click/bài |
| Chất lượng plan | Tỷ lệ plan bị từ chối; lý do từ chối phổ biến |
| Chất lượng publish | Tỷ lệ `META_CREATED`/`META_PARTIAL`; lỗi theo objective/adset bundle |
| Chống trùng | Số retry và số object được ledger bỏ qua đúng |
| Chất lượng creative | Kết quả theo media type, tầng phễu và creative |
| Hiệu quả AI tương lai | Tỷ lệ đề xuất được chấp nhận/sửa; chi phí API/plan; uplift so với baseline |

## 9. Lộ trình đề xuất

| Ưu tiên | Hạng mục | Điều kiện hoàn thành |
|---:|---|---|
| P0 | Regression Meta end-to-end với các bundle thật | Mỗi bundle có template đã kiểm chứng; tạo thử `PAUSED`; retry không trùng |
| P0 | Hoàn thiện báo lỗi cho người duyệt | Lỗi có cấp Campaign/Ad set/Ad, nguyên nhân dễ hiểu và link xử lý |
| P1 | Authentication nhân viên + audit | Biết ai tạo/sửa/gửi plan; quyền Content/Approver tách biệt |
| P1 | HTTPS/reverse proxy và vận hành server ổn định | Không mở port backend trực tiếp; backup `.web_state`; tự khởi động/restart |
| P1 | Bộ preset phễu chuẩn | Tầng 1/2/3 tách rõ, có exclusions và tài liệu dùng |
| P2 | AI creative assistant | Structured output, catalog validation, cache, cost limit, feedback/evals |
| P2 | Báo cáo hiệu quả nối với plan | Truy ngược performance về creative, flow, audience và tầng phễu |
| P3 | Cân nhắc hợp nhất dashboard | Chỉ sau khi auth, API và dữ liệu vận hành ổn định |

## 10. Một câu mô tả để giới thiệu

> Facebook Ads Khải Hoàn là công cụ nội bộ giúp đội Content gom nhiều bài Facebook thành các flow quảng cáo theo phễu, để IT duyệt cây Campaign–Ad set–Ad và tạo hàng loạt lên Meta ở trạng thái tạm dừng, nhanh hơn nhưng vẫn kiểm soát được cấu trúc, đối tượng, ngân sách và lỗi.
