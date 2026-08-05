# Facebook Ads Khải Hoàn

Tài liệu này là điểm bắt đầu chính thức để con người và AI agent hiểu toàn bộ workspace. Dự án là một công cụ nội bộ giúp đội Content và IT/Ads Operator biến nhiều bài viết có sẵn trên Facebook Page thành một kế hoạch quảng cáo có cấu trúc, duyệt kế hoạch và tạo Campaign → Ad set → Ad trên Meta bằng API.

> Trạng thái tài liệu: cập nhật ngày 04/08/2026 theo code hiện có. Công cụ đang trong giai đoạn vận hành nội bộ và hoàn thiện dần luồng Meta API. Không xem đây là hệ thống SaaS công khai.

## 1. Bài toán dự án giải quyết

Giao diện Ads Manager đi theo ba cấp và có nhiều lựa chọn kỹ thuật. Khi cần xử lý hàng chục hoặc hàng trăm bài, nhân viên Content khó thao tác nhanh và dễ tạo sai cấu trúc. Công cụ này gom nghiệp vụ thành một luồng dễ giao việc:

1. Tìm bài Page theo khoảng ngày hoặc dán nhiều link bài viết.
2. Xem nhanh creative: hình đại diện, nội dung và loại media.
3. Chọn một hoặc nhiều link rồi áp dụng cùng một “flow” quảng cáo.
4. Chọn mục tiêu, vị trí chuyển đổi, mục tiêu hiệu quả, tệp đối tượng, ngân sách, lịch và vị trí quảng cáo.
5. Dùng chiến dịch Meta có sẵn phù hợp hoặc tạo chiến dịch mới.
6. Gửi một snapshot bất biến để người duyệt kiểm tra cây Campaign → Ad set → Ads.
7. Chỉ sau khi duyệt, backend mới tạo tài sản Meta và luôn tạo ở trạng thái `PAUSED`.
8. Người thật kiểm tra lần cuối trong Ads Manager, sửa quảng cáo lỗi và chủ động bật chạy.

Giá trị chính không chỉ là “đăng quảng cáo nhanh”, mà là chuẩn hóa quyết định, gom đúng các ads cùng cấu hình vào cùng nhóm, giảm thao tác lặp và giữ con người ở bước kiểm soát rủi ro.

## 2. Người dùng và vai trò

| Vai trò | Trách nhiệm | Quyền chính |
|---|---|---|
| Content Marketing | Chuẩn bị bài, chọn link, cấu hình flow, gửi duyệt | Đọc catalog/preview, tạo kế hoạch và preset cục bộ |
| IT/Ads Operator | Kiểm tra cấu trúc, ngân sách, đối tượng, vị trí và lỗi Meta | Đăng nhập người duyệt, duyệt/từ chối, tạo tài sản Meta `PAUSED`, quét lỗi phân phối |
| Quản lý Marketing | Quyết định chiến lược phễu, ngân sách, quy tắc đặt tên và tiêu chuẩn duyệt | Xem kế hoạch và kết quả; phê chuẩn quy trình nghiệp vụ |
| Máy backend văn phòng | Giữ token và gọi Meta/Notion/Supabase | Là nơi duy nhất được giữ bí mật và thực hiện API ghi |

## 3. Nghiệp vụ phễu hiện tại

Định hướng mặc định cho Khải Hoàn:

| Tầng | Đối tượng | Mục tiêu thường dùng | Quy tắc loại trừ |
|---|---|---|---|
| Tầng 1 — lạnh | Người ở Phan Thiết, chủ yếu nữ; chưa tương tác | Video ưu tiên ThruPlay; ảnh/nội dung ưu tiên tương tác hoặc nhận biết | Loại tệp ấm và nóng để giảm chồng lấn |
| Tầng 2 — ấm | Người đã tương tác Page/bài viết hoặc đã thích bài | Chủ yếu tin nhắn | Loại người đã thuộc tầng chốt/remarketing |
| Tầng 3A — cân nhắc | Người đã nhắn tin nhưng còn phân vân | Tin nhắn/chốt tư vấn | Tách khỏi khách cũ khi cần thông điệp khác |
| Tầng 3B — khách cũ | Khách đã sử dụng dịch vụ | Remarketing, chăm sóc, upsell | Không trộn mặc định với người mới nhắn |

Không dùng một tệp gộp “đã tương tác + đã nhắn tin” làm tệp sản xuất mặc định vì sẽ khó đo lường và dễ chồng lấn giữa các tầng.

## 4. Kiến trúc workspace

```text
facebook ads khaihoan/
├─ README.md                         # Điểm vào tổng thể (tệp này)
├─ AGENTS.md                         # Quy tắc bắt buộc cho AI agent
├─ docs/
│  ├─ DEVELOPMENT_GUIDE.md           # Hướng dẫn phát triển và kiểm thử
│  ├─ PROJECT_FEATURE_NOTE.md        # Bảng thuyết minh dự án/tính năng
│  └─ meta-adset-copy-scheduling.md  # Ghi chú giới hạn Meta khi sao chép ad set
├─ Notion-facebook-ads-Khai-Hoan-1.1.0/
│  ├─ web_app.py                     # HTTP server, API và static web
│  ├─ web_ui/                        # Planner HTML/CSS/JavaScript
│  ├─ ads_core/                      # Nghiệp vụ Planner, review, Meta, preset
│  ├─ config/planner_bundles.json    # Catalog nghiệp vụ đang sử dụng
│  ├─ tests/                         # Unit/API/UI-contract và Playwright
│  ├─ gui_app.py                     # GUI Windows cũ/đường dự phòng
│  ├─ bulk_ads_tool.py               # Notion và CSV tương thích hệ thống cũ
│  └─ mcp_server.py                  # MCP riêng, không phải luồng chính hiện tại
└─ ads-dashboard/                    # Dashboard Next.js/Supabase tách biệt
```

Workspace có hai sản phẩm:

- `Notion-facebook-ads-Khai-Hoan-1.1.0/` là ứng dụng vận hành chính. Planner web và Meta API là hướng phát triển hiện tại; GUI/Notion/CSV vẫn là đường dự phòng.
- `ads-dashboard/` là dashboard theo dõi dùng Next.js và Supabase. Nó không sở hữu logic Planner và không được chứa token Meta.

## 5. Các module quan trọng

| Module | Trách nhiệm |
|---|---|
| `web_app.py` | Route HTTP, phục vụ frontend, session người duyệt, CSRF, ánh xạ lỗi dịch vụ thành HTTP response |
| `ads_core/planner_service.py` | Chuẩn hóa/validate payload, gom flow, dựng preview kế hoạch |
| `ads_core/planner_catalog.py` | Đọc/ghi catalog từ `config/planner_bundles.json` |
| `ads_core/creative_preview_service.py` | Lấy và cache nội dung/thumbnail/type của bài Facebook |
| `ads_core/preset_service.py` | CRUD preset đối tượng, ngân sách và vị trí; kết nối tệp Meta vào preset Planner |
| `ads_core/review_service.py` | Snapshot, trạng thái duyệt, publish và ledger chống tạo trùng |
| `ads_core/meta_service.py` | Meta Graph API: Page post, campaign, audience, preview, tạo tài sản và đọc lỗi phân phối |
| `ads_core/draft_service.py` | Tạo draft Notion an toàn và chống lặp cho đường cũ |
| `ads_core/export_service.py` | Xuất CSV chọn lọc cho đường dự phòng |
| `web_ui/app.js` | Trạng thái Planner, nhiều link/một flow, preview, review, preset và bảng lỗi |

## 6. Luồng dữ liệu chính

```text
Facebook Page links / Page posts theo ngày
                  │
                  ▼
        Creative preview qua backend
                  │
                  ▼
 Content chọn nhiều link + cấu hình một flow
                  │
                  ▼
 planner_service validate và dựng cây kế hoạch
                  │
                  ▼
 review_service lưu snapshot PENDING_REVIEW
                  │
                  ▼
 IT/Ads Operator đăng nhập → duyệt/từ chối
                  │
                  ▼
 meta_service tạo/reuse Campaign → tạo Ad set → Ads
                  │
                  ▼
 Tất cả PAUSED + lưu Meta ID vào publish ledger
                  │
                  ▼
 Con người kiểm tra Ads Manager, sửa lỗi, tự bật chạy
```

Một flow có thể áp dụng cho nhiều link. Các link cùng mục tiêu, campaign đích, đối tượng, vị trí chuyển đổi, mục tiêu hiệu quả, ngân sách/lịch và placement có thể nằm chung một ad set. Một bài cũng có thể xuất hiện trong nhiều flow để thử nhiều tầng hoặc cách chạy. Tool không ép mỗi ad thành một ad set riêng.

## 7. Trạng thái review và publish

Luồng chuẩn:

```text
PENDING_REVIEW → APPROVED → META_CREATED
                         └→ META_PARTIAL
PENDING_REVIEW → REJECTED
```

- Snapshot review không thay đổi theo bản nháp trên trình duyệt sau khi gửi.
- Publish chỉ chấp nhận kế hoạch đã duyệt.
- Ledger lưu ID ngay sau từng bước thành công; khi retry sẽ bỏ qua phần đã tạo.
- Một ad lỗi không làm mất các ad độc lập đã tạo thành công.
- `META_PARTIAL` nghĩa là cần người vận hành đọc chi tiết, sửa nguyên nhân rồi retry phần còn thiếu.

## 8. Các API chính

Đây là bản đồ định hướng, không thay thế code trong `web_app.py`:

| Nhóm | Endpoint tiêu biểu | Mục đích |
|---|---|---|
| Hệ thống | `GET /api/health`, `GET /api/config/status` | Kiểm tra server và trạng thái cấu hình không lộ secret |
| Planner | `GET /api/planner/catalog`, `POST /api/planner/preview` | Catalog và preview đã validate |
| Bài viết | `GET /api/meta/page-posts`, `POST /api/meta/creative-previews` | Tìm bài theo ngày và hiển thị creative |
| Meta đọc | `GET /api/meta/status`, `/campaigns`, `/audiences` | Kiểm tra kết nối và tải tài sản có thể chọn |
| Preset | `GET/POST /api/presets/{kind}`, `PUT /api/presets/{kind}/{code}` | Quản lý preset Planner |
| Review | `POST /api/reviews`, `GET /api/reviews/{id}` | Gửi và đọc snapshot duyệt |
| Người duyệt | `POST /api/auth/approver`, `GET /api/auth/me`, `DELETE /api/auth/session` | Tạo/đọc/xóa phiên người duyệt |
| Quyết định | `POST /api/reviews/{id}/approve|reject|publish` | Duyệt, từ chối và publish |
| Meta ghi | `POST /api/meta/audiences/create`, `POST /api/meta/drafts` | Tạo tệp hoặc tài sản quảng cáo; yêu cầu người duyệt |
| Chẩn đoán | `POST /api/meta/delivery-issues` | Đọc ads lỗi/chờ duyệt/tạm dừng, không tự sửa hoặc xóa |
| Dự phòng | `/api/planner/drafts`, `/api/export`, `/api/export/candidates` | Notion draft và CSV cũ |

## 9. Tính năng hiện có

- Lấy bài Page theo khoảng ngày và nhập tất cả vào Planner.
- Dán nhiều link, chọn tất cả/chọn từng bài, xóa link và tự sửa các flow liên quan.
- Preview creative gồm Page, nội dung rút gọn, thumbnail và loại media.
- Một flow áp dụng đồng thời cho nhiều link; duplicate/edit/delete flow.
- Tạo campaign mới hoặc reuse campaign Meta cùng ad account, objective và trạng thái hợp lệ.
- Cấu hình ngân sách ngày/trọn đời, lịch bắt đầu/kết thúc và đơn vị tiền theo ad account.
- Thư viện preset đối tượng, ngân sách, dataset và placement.
- Màn hình đối tượng theo tinh thần Meta: loại tệp, kiểm soát bắt buộc, gợi ý mở rộng và loại trừ.
- Đọc/tạo Custom Audience Page Engagers hoặc Page Messagers rồi lưu thành preset.
- Cây kiểm duyệt Campaign → Ad set → Ads.
- Publish an toàn `PAUSED`, ledger chống trùng và báo kết quả từng ad.
- Bảng ads cần xử lý: lỗi, chờ duyệt, tạm dừng; ẩn ads đang hoạt động khỏe; có link Ads Manager.
- Đường Notion/CSV và dashboard Supabase vẫn còn để dự phòng/đối chiếu.

## 10. Chưa hoàn thành hoặc không được hiểu nhầm

- AI phân tích creative và tự đề xuất kế hoạch chưa phải tính năng production. Kiến trúc dự kiến dùng OpenAI Responses API + Structured Outputs ở backend, nhưng chỉ hoạt động sau khi có `OPENAI_API_KEY` và triển khai validation.
- Công cụ không tự bật, tắt hay xóa quảng cáo thật. Việc thay đổi phân phối cuối cùng do người có quyền thực hiện trong Meta.
- MCP/ChatGPT Web không phải hạ tầng bắt buộc và hiện không phải đường vận hành chính.
- Không phải mọi loại Custom Audience/Lookalike của Meta đã được hỗ trợ tạo mới. Hiện ưu tiên Page engagement/messaging và đọc những tệp đã có.
- Backend HTTP hiện phù hợp localhost/LAN tin cậy. Không public trực tiếp ra Internet khi chưa có lớp xác thực nhân viên, HTTPS, reverse proxy và kiểm soát truy cập.

## 11. Cài đặt và chạy

Yêu cầu:

- Windows server/văn phòng chạy Python 3.11 trở lên.
- Node.js chỉ cần khi chạy Playwright E2E.
- Meta System User token lâu dài có đúng quyền với ad account và Page.

```powershell
Set-Location 'D:\code facebook ads khaihoan\Notion-facebook-ads-Khai-Hoan-1.1.0'
Copy-Item .env.example .env
pip install -r requirements.txt
```

Điền `.env` trên máy backend. Không dán token vào chat, tài liệu, frontend hoặc git.

Chạy chỉ trên máy hiện tại:

```powershell
.\run_web.bat
```

Chạy trong mạng LAN văn phòng:

```powershell
.\run_web_lan.bat
```

Máy nhân viên truy cập `http://IP-MAY-SERVER:8000`. Windows Firewall phải cho phép TCP 8000 trong profile mạng nội bộ. Khi truy cập ngoài LAN, cần HTTPS và lớp xác thực; không mở thẳng port này ra Internet.

## 12. Biến môi trường quan trọng

| Biến | Ý nghĩa | Nơi được phép |
|---|---|---|
| `META_ACCESS_TOKEN` | System User token gọi Marketing API | Chỉ trong backend `.env` |
| `META_AD_ACCOUNT_ID` | Tài khoản quảng cáo dạng `act_...` | Backend |
| `META_PAGE_ID` | Page chứa bài viết có sẵn | Backend |
| `META_API_VERSION` | Phiên bản Graph API | Backend |
| `META_TEST_MODE` | Chế độ bảo vệ/test của tích hợp Meta | Backend |
| `META_ADSET_TEMPLATE_MAP` | Ánh xạ bundle Planner → ad set mẫu đã kiểm chứng | Backend |
| `PLANNER_APPROVER_KEY` | Mật khẩu người duyệt | Backend, không dùng lại secret khác |
| `PLANNER_SESSION_SECRET` | Ký cookie phiên duyệt | Backend, khác approver key |
| `OPENAI_API_KEY` | Dành cho AI creative trong tương lai | Backend; hiện chưa bắt buộc |
| `NOTION_*`, `SUPABASE_*`, `TELEGRAM_*` | Tích hợp cũ/dự phòng | Backend hoặc desktop theo cấu hình |

Đọc `.env.example` trong ứng dụng để có danh sách đầy đủ. Không đưa giá trị thật vào tài liệu.

## 13. Bảo mật và quy tắc bất biến

- Secret chỉ ở backend `.env`; không log, screenshot, commit hoặc trả về frontend.
- Phiên người duyệt dùng cookie `HttpOnly`, `SameSite=Strict`; thao tác nhạy cảm dùng CSRF token.
- Mọi lệnh ghi Meta phải đi qua quyền người duyệt.
- Campaign, ad set và ad do tool tạo luôn là `PAUSED`.
- Tạo Custom Audience cần xác nhận điều khoản rõ ràng.
- Campaign có sẵn phải thuộc ad account đã chọn, cùng objective và ở trạng thái `ACTIVE`/`PAUSED`.
- Không tự động xóa hay kích hoạt tài sản Meta thật.
- Không chạy test live có ghi Meta nếu chưa được chủ dự án xác nhận rõ phạm vi.

## 14. Kiểm thử

Từ thư mục ứng dụng:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
node --check web_ui/app.js
node --check tests/e2e/planner.spec.js
npm install
npm run test:e2e
```

E2E live Meta được khóa bằng biến môi trường và chỉ chạy khi có phê duyệt:

```powershell
$env:LIVE_META_TEST='1'
node node_modules/@playwright/test/cli.js test tests/e2e/planner.live.spec.js --project='máy tính'
```

Mốc kiểm chứng gần nhất: 66 unit/API/UI-contract tests passed; delivery dashboard 2/2 E2E (desktop + mobile); bộ Planner trước lần bổ sung gần nhất từng đạt 34/34 E2E. Có một test CSV legacy lệch tên preset cũ với catalog hiện tại; cần sửa fixture hoặc xác nhận quy tắc tên trước khi coi là regression sản phẩm.

## 15. Dữ liệu runtime và xử lý sự cố

- Review và publish ledger mặc định nằm trong `.web_state/`; đây là dữ liệu runtime, không chỉnh tay khi server đang chạy.
- Draft Planner chưa gửi duyệt được giữ trong `localStorage` của trình duyệt.
- Nếu đổi `.env` hoặc code backend, phải restart server Python.
- Nếu creative không hiện: kiểm tra Page permission, Page token, link có thuộc Page cấu hình và endpoint `/api/meta/status?verify=true`.
- Nếu máy khác trong LAN không vào được: kiểm tra server bind `0.0.0.0`, IP nội bộ, cùng mạng và Windows Firewall.
- Nếu Meta báo lỗi: giữ nguyên tài sản thành công, đọc lỗi từng ad, sửa cấu hình và retry; ledger sẽ bỏ qua phần đã tạo.
- Sandbox của agent có thể chặn kết nối Graph API với `WinError 10013`; hãy xác nhận lại trên phiên Windows backend bình thường trước khi kết luận token/code hỏng.

## 16. Tài liệu tiếp theo

- [Hướng dẫn phát triển](docs/DEVELOPMENT_GUIDE.md)
- [Bảng giới thiệu dự án và tính năng](docs/PROJECT_FEATURE_NOTE.md)
- [Quy tắc cho AI agent](AGENTS.md)
- [Cấu trúc lịch sử của workspace](PROJECT_STRUCTURE.md)
- [Giới hạn copy/schedule ad set của Meta](docs/meta-adset-copy-scheduling.md)
