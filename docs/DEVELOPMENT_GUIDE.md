# Hướng dẫn phát triển Facebook Ads Khải Hoàn

Tài liệu này dành cho developer và AI agent tiếp tục dự án. Đọc [README tổng thể](../README.md) trước để hiểu nghiệp vụ.

## 1. Mục tiêu kỹ thuật

Hệ thống cần giúp nhân viên thao tác nhanh nhưng không làm mất các lớp kiểm soát của Meta. Kiến trúc ưu tiên:

- Một nguồn validation ở backend.
- Frontend dễ dùng cho người không chuyên Ads Manager.
- Nhiều bài có thể dùng chung một flow và gom đúng campaign/ad set.
- Snapshot duyệt có thể truy vết.
- Ghi Meta an toàn, `PAUSED`, retry được và không tạo trùng.
- Tích hợp AI chỉ đưa ra đề xuất có cấu trúc; không tự vượt quyền duyệt.

## 2. Ranh giới module

### HTTP và giao diện

- `web_app.py`: parse request, gọi service, auth/session/CSRF, HTTP status và response JSON.
- `web_ui/index.html`: cấu trúc semantic và các vùng màn hình.
- `web_ui/app.js`: state trình duyệt, render, event, gọi API.
- `web_ui/styles.css`: layout responsive và trạng thái trực quan.

Không đặt logic gọi Graph API trực tiếp trong frontend. Không đưa secret vào HTML/JS hoặc biến môi trường public.

### Nghiệp vụ

- `planner_service.py`: schema và invariant của plan/flow.
- `planner_catalog.py`: persistence của catalog JSON.
- `preset_service.py`: validate/CRUD preset.
- `review_service.py`: review state machine, immutable snapshot và publish ledger.
- `meta_service.py`: adapter Meta Graph API và chuyển plan thành Meta objects.
- `creative_preview_service.py`: đọc creative, cache và fallback preview.
- `draft_service.py`, `export_service.py`: đường Notion/CSV dự phòng.

Nếu thêm hành vi, ưu tiên đặt ở module sở hữu dữ liệu thay vì thêm điều kiện rải rác trong `web_app.py` hoặc `app.js`.

## 3. Mô hình Planner

Một payload gồm danh sách link và danh sách `flows`. Flow là một cách chạy áp dụng lên một tập link, thường gồm:

```json
{
  "id": "flow-id",
  "campaign_code": "ENG_BASE",
  "campaign_mode": "new",
  "meta_campaign_id": null,
  "adset_code": "...",
  "link_urls": ["https://www.facebook.com/..."],
  "audience_codes": ["..."],
  "dataset_code": "...",
  "budget_code": "...",
  "custom_budget_values": {"Ngân sách/ngày": "..."},
  "start_time": "2026-08-04T09:00",
  "end_time": null,
  "placement_code": "...",
  "creative_mode": "existing_post"
}
```

Đây chỉ là ví dụ cấu trúc; code và catalog hiện tại là nguồn chuẩn cho code hợp lệ.

### Quy tắc gom nhóm

- Nhiều link cùng flow tạo nhiều ads dưới cùng cấu trúc ad set.
- Một link có thể thuộc nhiều flow để chạy nhiều tầng/cách thử.
- Không gom hai flow nếu khác campaign đích, objective, conversion location, performance goal, audience, dataset, budget/lịch hoặc placement.
- Khi xóa link, phải xóa link khỏi mọi flow; flow không còn link phải được loại bỏ.
- Khi sửa flow, giữ ID ổn định nếu có thể để UI và retry dễ truy vết.

### Campaign có sẵn

Chỉ cho reuse khi campaign:

- thuộc `META_AD_ACCOUNT_ID` hiện tại;
- cùng objective với bundle Planner;
- có trạng thái `ACTIVE` hoặc `PAUSED`;
- còn truy cập được ở thời điểm backend validate/publish.

Không tin hoàn toàn vào ID do browser gửi lên; backend phải kiểm tra lại.

## 4. Catalog và preset

Catalog nằm tại `config/planner_bundles.json` với các nhóm chính:

- `campaignBundles`
- `adSetBundles`
- `audiencePresets`
- `datasetPresets`
- `budgetPresets`
- `placementPresets`

### Khi thêm campaign/ad set bundle

1. Xác định objective, conversion location và performance goal thật trên Meta.
2. Tạo code ổn định, không dùng label làm ID.
3. Khai báo audience được phép để tránh chọn sai tầng.
4. Nếu publish qua Meta, ánh xạ `adset_code` sang một ad set mẫu đã chạy đúng trong `META_ADSET_TEMPLATE_MAP`.
5. Không bật `META_ALLOW_DEFAULT_TEMPLATE` chỉ để né mapping; chỉ bật nếu mọi bundle thật sự dùng chung cấu hình tối ưu.
6. Thêm test validation và Meta preview/publish tương ứng.

### Khi thêm/sửa preset

- Tách `code`, tên hiển thị và `notionValues`/giá trị kỹ thuật.
- Đối tượng phải phân biệt rõ broad/custom/lookalike.
- “Kiểm soát đối tượng” là giới hạn bắt buộc; “Gợi ý đối tượng” cho phép Meta mở rộng theo cơ chế tối ưu.
- Detailed targeting và exclusion có thể để trống; không ép nhân viên điền khi nghiệp vụ không cần.
- Placement phải mô tả đúng lựa chọn Meta đang hỗ trợ, đặc biệt thiết bị, nền tảng và feed/reels/search.
- Luôn bảo toàn preset người dùng đã lưu; migration cần rõ ràng và có backup/test.

## 5. Tích hợp Meta

### Đọc bài và creative

Backend resolve link thành `object_story_id`/`effective_object_story_id`. Link numeric có thể xử lý trực tiếp; `pfbid` hoặc permalink cần Page access và có thể phải dò `published_posts`. Preview không lấy được không nên chặn lập kế hoạch, nhưng publish bằng bài có sẵn phải resolve được story hợp lệ.

### Tạo tài sản

Thứ tự an toàn:

1. Validate plan và cấu hình backend.
2. Resolve toàn bộ bài có sẵn.
3. Reuse hoặc tạo Campaign `PAUSED`.
4. Tạo Ad set `PAUSED` theo template đã kiểm chứng + ngân sách/lịch/targeting của plan.
5. Tạo creative/ad dùng bài có sẵn và ad `PAUSED`.
6. Ghi ID vào ledger ngay sau từng bước thành công.
7. Trả kết quả từng phần, gồm lỗi cụ thể và số đối tượng đã tạo.

Không biến publish thành một transaction giả: Meta không rollback đồng bộ ba cấp. Ledger và báo cáo partial là cơ chế phục hồi chính.

### Custom Audience

Tạo audience là thao tác ghi Meta. Luồng HTTP cần:

- phiên approver hợp lệ;
- CSRF token;
- payload xác nhận điều khoản;
- validate preset cục bộ trước khi gọi Meta;
- chỉ lưu preset sau khi Meta trả audience hợp lệ.

### Delivery issues

Dashboard lỗi chỉ đọc. Nó nhóm Campaign → Ad set → Ad, ưu tiên `issues_info` và `ad_review_feedback`, phân loại error/pending/paused và ẩn active healthy ads. Không tự sửa, bật, tắt hoặc xóa.

## 6. Review, auth và CSRF

### Review invariant

- `submit_review` lưu snapshot đã validate.
- `decide_review` chỉ cho chuyển trạng thái hợp lệ.
- `publish_review` chỉ publish bản đã `APPROVED`.
- Không publish payload mới do browser thay thế sau duyệt.
- Cùng yêu cầu retry phải reuse ledger, không tạo lại Meta object đã có ID.

### Session approver

- Approver key so sánh bằng constant-time comparison.
- Cookie phải là `HttpOnly`, `SameSite=Strict`; thêm `Secure` khi đi qua HTTPS.
- Tất cả POST nhạy cảm phải kiểm tra CSRF.
- Logout phải xóa cookie.
- Không trả secret/signing material trong API status.

Hiện ứng dụng chưa có tài khoản riêng cho mọi nhân viên. Vì vậy chỉ chạy trong LAN tin cậy hoặc đặt sau reverse proxy có HTTPS và authentication.

## 7. API và lỗi

Quy ước hiện tại:

- Response thành công có `{"ok": true, ...}`.
- Response lỗi có `{"ok": false, "error": "..."}`.
- Validation đầu vào: 400.
- Chưa đăng nhập/CSRF/quyền: 403; credential sai có thể là 401.
- Xung đột review state: 409.
- Meta upstream lỗi: 502.
- Thiếu cấu hình server: dùng 4xx/503 phù hợp, không lộ giá trị secret.

Khi thêm endpoint:

1. Đặt tên theo resource, không theo nút UI.
2. Validate kiểu và giới hạn kích thước payload.
3. Xác định endpoint đọc hay ghi và bắt auth/CSRF đúng mức.
4. Không trả raw exception chứa token/request URL.
5. Thêm test handler và test service riêng.
6. Cập nhật bảng API trong README nếu endpoint có ý nghĩa nghiệp vụ mới.

## 8. UI/UX conventions

- Ngôn ngữ người dùng là tiếng Việt rõ nghĩa; code/ID kỹ thuật giữ ASCII ổn định.
- Một thời điểm chỉ trình bày một flow đang cấu hình; nhiều link có thể được chọn cho flow đó.
- Luôn cho thấy số bài đang chọn và tóm tắt flow đã tạo.
- Có thao tác sửa, nhân bản, xóa flow; xóa link không để state mồ côi.
- Preview lỗi phải có fallback dễ hiểu và không làm vỡ layout.
- Cấu trúc review phải giống mô hình Meta ba cấp để người duyệt đối chiếu nhanh.
- Cảnh báo rõ khi hành động sẽ gọi Meta; nút publish không đồng nghĩa bật chạy.
- Kiểm tra desktop và mobile. Tránh bảng ngang không cuộn hoặc modal không đóng được.

## 9. Tích hợp AI trong tương lai

Mục tiêu AI là đọc nội dung/loại media rồi gợi ý tầng phễu, objective, performance goal, audience, placement, ngân sách thử nghiệm và giải thích. AI không được tự bịa code preset hoặc gọi Meta ghi.

Kiến trúc đề xuất:

```text
Creative đã chuẩn hóa
  → backend tạo prompt có catalog + quy tắc phễu
  → OpenAI Responses API với Structured Outputs
  → validate JSON bằng schema + catalog hiện tại
  → hiển thị “đề xuất”, người dùng sửa/chấp nhận
  → quy trình review bình thường
```

Yêu cầu:

- `OPENAI_API_KEY` chỉ ở backend.
- Gửi nội dung cần thiết, không gửi token/PII không cần thiết.
- Có giới hạn số bài/batch, timeout, retry và theo dõi chi phí.
- Cache theo creative ID/nội dung/model/prompt version.
- Lưu cả đề xuất, lý do, model và prompt version để audit.
- Nếu AI lỗi, Planner thủ công vẫn hoạt động.
- Không mô tả AI là “tự học” nếu chỉ lưu note. Muốn cải thiện phải có bộ dữ liệu feedback, versioned rules/evals và quy trình duyệt thay đổi skill/prompt.

## 10. Kiểm thử

### Unit/API/UI contract

```powershell
& 'C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s tests -p 'test_*.py'
```

Ưu tiên chạy file test gần module sửa trước, sau đó chạy discover. Tests dùng `unittest`, không giả định `pytest` đã được cài.

### JavaScript syntax

```powershell
node --check web_ui/app.js
node --check tests/e2e/planner.spec.js
```

### Playwright

Khởi động server hoặc dùng script của dự án:

```powershell
npm install
npm run test:e2e
```

Nếu server đã chạy:

```powershell
$env:PLAYWRIGHT_EXTERNAL_SERVER='1'
node node_modules/@playwright/test/cli.js test tests/e2e/planner.spec.js
```

Live Meta E2E chỉ khi chủ dự án cho phép rõ ràng. Giữ `LIVE_META_TEST` tắt mặc định.

### Checklist regression nghiệp vụ

- Import bài theo ngày → chọn tất cả → link xuất hiện đủ.
- Xóa một link → selection và mọi flow cập nhật đúng.
- Một flow + nhiều link → số ads đúng, cùng ad set.
- Một link + nhiều flow → xuất hiện trong từng nhánh đúng.
- Existing campaign chỉ hiện cùng objective và được backend kiểm tra lại.
- Review tree đúng campaign/ad set/ad, snapshot không đổi.
- Reject không publish; approve chưa tự publish.
- Publish tạo `PAUSED`; retry không tạo trùng.
- Một ad lỗi trả partial và các ad còn lại vẫn có kết quả.
- Delivery scan ẩn active healthy, hiển thị lỗi/review/paused và Ads Manager link.
- Session approver đóng/mở/logout được; request sai CSRF bị chặn.

## 11. Git và dữ liệu người dùng

- Luôn xem `git status --short` trước khi sửa.
- Worktree có thể đang dirty; không revert thay đổi của người dùng.
- Không format hoặc rewrite toàn bộ `planner_bundles.json` nếu không cần.
- Không commit `.env`, `.web_state`, exports, cache, build, token hoặc ảnh chụp chứa secret.
- Không dùng `git reset --hard` hoặc checkout phá thay đổi.
- Mỗi thay đổi nên có diff nhỏ, test tương ứng và ghi rõ phần chưa kiểm chứng live.

## 12. Definition of Done

Một thay đổi được coi là hoàn tất khi:

1. Đúng nghiệp vụ và không phá các invariant an toàn.
2. Backend validate mọi dữ liệu ảnh hưởng Meta.
3. UI có trạng thái loading/error/empty/success hợp lý.
4. Unit/API/UI-contract liên quan qua.
5. E2E liên quan qua hoặc giới hạn môi trường được nêu bằng bằng chứng.
6. `git diff --check` sạch và diff không chứa secret.
7. README/dev guide/feature note được cập nhật nếu hành vi người dùng hoặc vận hành thay đổi.
