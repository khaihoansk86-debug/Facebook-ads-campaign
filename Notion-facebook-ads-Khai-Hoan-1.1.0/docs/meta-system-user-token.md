# Meta Marketing API: System User access token

Cập nhật: 2026-07-28.

## Kết luận cho dự án

Backend nên dùng **System User access token** do Business Portfolio (Business Manager/BM) tạo, không dùng token của Graph API Explorer. Token phải nằm ở backend; không đưa vào frontend Vercel, JavaScript trình duyệt, Git, ảnh chụp hoặc log.

Để tạo và dùng được token, phải có đủ cả ba lớp:

1. App Meta được Business Portfolio sở hữu hoặc thêm vào portfolio.
2. System User được gán đúng tài sản và quyền trên tài sản đó.
3. Token được tạo cho app với đúng permission scope.

Có scope trong token nhưng chưa gán Ad Account/Page cho System User vẫn không đủ quyền. Ngược lại, gán tài sản nhưng token thiếu scope cũng không đủ.

Nguồn chính thức:

- [Meta Marketing API — System Users](https://developers.facebook.com/docs/marketing-api/system-users/)
- [Meta Marketing API — Authorization](https://developers.facebook.com/docs/marketing-api/overview/authorization/)
- [Meta Access Tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/)
- [Meta Business Help Center](https://www.facebook.com/business/help/)

## Điều kiện chuẩn bị

- Có Business Portfolio/BM.
- Người thiết lập có quyền quản trị portfolio, đủ quyền quản lý System User, app và tài sản.
- Meta app đã được thêm/claim vào đúng portfolio.
- Ad Account và Page cần chạy quảng cáo nằm trong portfolio hoặc được chia sẻ cho portfolio.
- Nếu dùng Instagram identity, Pixel/Dataset, Catalog hoặc tài sản khác, cũng phải gán chúng cho System User.
- App phải có cấp truy cập phù hợp đối với các permission được dùng. App Review, Advanced Access hoặc Business Verification có thể được Meta yêu cầu tùy permission, loại tài sản và việc app truy cập tài sản của doanh nghiệp khác; việc tạo System User token tự nó không thay thế các yêu cầu đó.

Meta phân biệt System User kiểu quản trị và nhân viên. Nên dùng quyền tối thiểu cần thiết; chỉ dùng System User quản trị khi luồng thật sự cần quản lý rộng toàn portfolio.

## Quy trình tạo

Tên menu có thể thay đổi nhẹ giữa **Business Settings** và giao diện **Business Portfolio settings**, nhưng luồng nghiệp vụ là:

1. Mở Business Settings của đúng portfolio.
2. Vào **Users → System users** và tạo System User.
3. Chọn System User, bấm **Add assets/Assign assets**.
4. Gán:
   - Ad Account: quyền quản lý/tạo chiến dịch (`Manage campaigns` hoặc quyền tương đương).
   - Page: quyền tạo quảng cáo và đọc nội dung Page cần dùng; nếu đang thiết lập thử nghiệm có thể gán Full control, sau đó thu hẹp theo nguyên tắc tối thiểu.
   - Instagram account: nếu quảng cáo dùng danh tính hoặc placement Instagram.
   - Pixel/Dataset/Catalog: chỉ khi nghiệp vụ quảng cáo cần những tài sản đó.
5. Đảm bảo app đã được thêm vào portfolio và System User được phép dùng app đó.
6. Trong System User, chọn **Generate new token**.
7. Chọn đúng app, chọn thời hạn token mà giao diện đang cung cấp, rồi chọn các permission cần thiết.
8. Sao chép token một lần vào secret store hoặc `.env` của backend. Meta không hiển thị lại toàn bộ secret sau đó.
9. Kiểm tra token bằng Access Token Debugger hoặc `GET /debug_token`, sau đó chạy các request đọc tối thiểu trước khi cho phép tạo dữ liệu.

Nguồn chính thức:

- [Meta Marketing API — System Users](https://developers.facebook.com/docs/marketing-api/system-users/)
- [Meta Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)
- [Graph API `debug_token` reference](https://developers.facebook.com/docs/graph-api/reference/debug_token/)

## Permission nên chọn cho Planner

| Permission | Dùng cho | Ghi chú |
|---|---|---|
| `ads_management` | Tạo/sửa Campaign, Ad Set, Ad và Creative | Quyền bắt buộc cho luồng publish qua Marketing API |
| `ads_read` | Đọc Campaign/Ad Set/Ad, trạng thái và báo cáo | Nên chọn để preview, đối soát và hồi quy |
| `business_management` | Đọc/quản lý cấu trúc portfolio và các tài sản được gán | Cần khi tool liệt kê BM, Ad Account hoặc quản lý tài sản; không thay thế `ads_management` |
| `pages_show_list` | Liệt kê các Page mà danh tính có quyền | Cần nếu UI cho chọn Page thay vì chỉ dùng Page ID cố định |
| `pages_read_engagement` | Đọc nội dung/metadata và engagement của Page | Cần cho việc tra cứu/xác minh bài viết có sẵn |

Nếu chỉ truyền `object_story_id` đã biết, Meta vẫn kiểm tra quyền của app/System User đối với Page và Ad Account. Vì vậy Page phải được gán cho System User; token có `pages_read_engagement` nhưng không có quyền tài sản Page là chưa đủ.

Không chọn thêm `pages_manage_posts` chỉ để chạy lại một bài có sẵn. Permission đó chỉ hợp lý khi tool cần tạo hoặc sửa bài viết Page. Các nghiệp vụ Page/Instagram khác phải bổ sung scope theo đúng endpoint thực tế, không cấp trước hàng loạt.

Nguồn chính thức:

- [`ads_management`](https://developers.facebook.com/docs/permissions/ads_management/)
- [`ads_read`](https://developers.facebook.com/docs/permissions/ads_read/)
- [`business_management`](https://developers.facebook.com/docs/permissions/business_management/)
- [`pages_show_list`](https://developers.facebook.com/docs/permissions/pages_show_list/)
- [`pages_read_engagement`](https://developers.facebook.com/docs/permissions/pages_read_engagement/)
- [Meta Marketing API — Access and Authentication](https://developers.facebook.com/docs/marketing-api/overview/authorization/)

## Thời hạn token

Graph API Explorer thường tạo **User access token ngắn hạn**, gắn với tài khoản Facebook cá nhân đang đăng nhập. Token ngắn hạn thường chỉ tồn tại khoảng một đến hai giờ; User token có thể được đổi sang loại dài hạn, thường khoảng 60 ngày. Nó vẫn phụ thuộc vào phiên/người dùng và không thích hợp làm secret cố định cho backend.

System User token được tạo trong Business Settings cho machine-to-machine automation. Giao diện Meta có thể cho chọn thời hạn như **60 days** hoặc **Never** tùy cấu hình và chính sách hiện hành. `Never` nghĩa là không có ngày hết hạn cố định, **không có nghĩa token không thể bị thu hồi hoặc vô hiệu**.

Không nên suy đoán thời hạn từ loại token. Sau khi tạo, kiểm tra các trường `type`, `application`, `scopes`, `data_access_expires_at`, `expires_at` và `is_valid` bằng Access Token Debugger/`debug_token`. Backend cũng nên cảnh báo trước khi token có ngày hết hạn.

Nguồn chính thức:

- [Meta Access Tokens — User access tokens and expiration](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/)
- [Meta Marketing API — System Users](https://developers.facebook.com/docs/marketing-api/system-users/)
- [Graph API `debug_token`](https://developers.facebook.com/docs/graph-api/reference/debug_token/)

## Khi nào token hoặc quyền truy cập mất hiệu lực

Token có thể không dùng được khi:

- Đến ngày hết hạn đã chọn.
- Token bị thu hồi/xóa hoặc System User bị xóa/vô hiệu.
- App bị xóa khỏi portfolio, bị vô hiệu, hoặc quyền truy cập của app bị thu hồi.
- Permission scope bị thu hồi hoặc app không còn cấp truy cập cần thiết.
- Ad Account, Page hoặc tài sản bị bỏ gán khỏi System User/portfolio.
- System User hoặc portfolio mất quyền đối với tài sản được chia sẻ từ doanh nghiệp khác.
- Meta vô hiệu token/app vì lý do bảo mật, chính sách hoặc phát hiện rủi ro.
- Ad Account/Page bị hạn chế, vô hiệu hoặc không còn đủ điều kiện quảng cáo; trường hợp này token có thể vẫn `is_valid=true` nhưng request vào tài sản sẽ thất bại.

Vì vậy cần kiểm tra riêng:

1. token có hợp lệ không;
2. token còn đủ scope không;
3. System User còn được gán đúng tài sản không;
4. từng tài sản còn hoạt động và cho phép quảng cáo không.

Nguồn chính thức:

- [Meta Access Tokens — invalidation and expiration](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/)
- [Graph API `debug_token`](https://developers.facebook.com/docs/graph-api/reference/debug_token/)
- [Meta Platform Terms](https://developers.facebook.com/terms/)

## So sánh với token Graph API Explorer

| Thuộc tính | Graph API Explorer User token | System User token |
|---|---|---|
| Danh tính | Người dùng Facebook cá nhân | Danh tính máy của Business Portfolio |
| Mục đích | Thử endpoint và gỡ lỗi tương tác | Backend/automation ổn định |
| Vòng đời | Mặc định ngắn hạn; loại dài hạn vẫn thường khoảng 60 ngày | Chọn thời hạn trong Business Settings; có thể có tùy chọn không ngày hết hạn |
| Phụ thuộc người dùng | Có | Không phụ thuộc phiên đăng nhập cá nhân |
| Gán tài sản | Theo quyền của người dùng/app | Phải gán tài sản trực tiếp cho System User |
| Phù hợp production | Không | Có, nếu bảo vệ secret và giới hạn quyền đúng |

## Checklist triển khai cho dự án

- [ ] App nằm trong đúng BM/Business Portfolio.
- [ ] System User riêng cho backend Planner, không dùng chung với thao tác thủ công.
- [ ] Gán đúng `TKQC US` và Page chứa bài viết.
- [ ] Gán Instagram account nếu dùng placement/danh tính Instagram.
- [ ] Token có `ads_management`, `ads_read`, `business_management`, `pages_show_list`, `pages_read_engagement` theo nhu cầu hiện tại.
- [ ] Kiểm tra `debug_token`; lưu app ID, scopes và ngày hết hạn, không lưu token vào log.
- [ ] Thử `GET /me/adaccounts`, Page/post read và Campaign read.
- [ ] Chạy một vòng tạo `PAUSED` và xác minh idempotency.
- [ ] Đưa token vào secret của backend production; frontend chỉ gọi API nội bộ đã xác thực.
- [ ] Có quy trình xoay token và cảnh báo khi quyền/tài sản bị thu hồi.

