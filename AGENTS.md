# Hướng dẫn bắt buộc cho AI agent

Phạm vi áp dụng: toàn bộ workspace `facebook ads khaihoan/`.

## Trước khi làm việc

1. Đọc [README.md](README.md) để hiểu sản phẩm, vai trò, luồng duyệt và giới hạn hiện tại.
2. Đọc [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) trước khi sửa code.
3. Nếu công việc liên quan UI/nghiệp vụ, đọc [docs/PROJECT_FEATURE_NOTE.md](docs/PROJECT_FEATURE_NOTE.md).
4. Ứng dụng chính nằm tại `Notion-facebook-ads-Khai-Hoan-1.1.0/`; `ads-dashboard/` là sản phẩm phụ tách biệt.
5. Vì repository có `.codegraph/`, dùng `codegraph explore "..."` trước khi grep/đọc rộng để tìm symbol, call path và blast radius.
6. Chạy `git status --short` và giữ nguyên mọi thay đổi không thuộc nhiệm vụ. Không reset, checkout hoặc ghi đè cấu hình người dùng.

## Quy tắc kiến trúc

- `web_app.py` chỉ điều phối HTTP/auth/error; nghiệp vụ nằm trong `ads_core/`.
- `planner_service.py` là nguồn chuẩn cho validation và preview plan.
- `config/planner_bundles.json` là dữ liệu nghiệp vụ thật; không đổi tên/code/preset hàng loạt khi chưa có yêu cầu rõ.
- Frontend không được tự tái định nghĩa quy tắc quan trọng mà backend chưa validate.
- Giữ Notion/CSV hoạt động như fallback cho đến khi chủ dự án yêu cầu loại bỏ.
- Không chuyển Planner logic sang `ads-dashboard/` ngoài một nhiệm vụ migration riêng.

## Quy tắc an toàn Meta và secret

- Không đọc/in/chụp/commit giá trị thật trong `.env`, token hoặc cookie.
- Không đặt `META_ACCESS_TOKEN`, OpenAI key, Notion token, Supabase secret hay approver key trong frontend.
- Mọi tài sản Meta do tool tạo phải là `PAUSED`.
- Mọi thao tác ghi Meta phải yêu cầu phiên approver + CSRF ở lớp HTTP.
- Không tự bật, tắt hoặc xóa tài sản Meta thật.
- Không chạy script/test live ghi Meta nếu người dùng chưa xác nhận cụ thể.
- Khi retry publish, phải giữ tính idempotent và không phá ledger của tài sản đã tạo.
- Một lỗi ad độc lập không được làm mất kết quả thành công của ads khác; duy trì báo cáo `META_PARTIAL`.

## Quy trình sửa code

1. Dùng CodeGraph tìm luồng gọi và tests liên quan.
2. Đọc đúng module và test gần nhất; tránh refactor ngoài phạm vi.
3. Với hành vi mới, thêm hoặc cập nhật unit/API/UI-contract test.
4. Nếu đổi UI flow, cập nhật Playwright phù hợp cho desktop và mobile khi cần.
5. Chạy kiểm tra tối thiểu liên quan; sau đó mới chạy bộ rộng.
6. Dùng `git diff --check` và xem diff cuối để phát hiện lỗi encoding/whitespace/secret.
7. Cập nhật tài liệu nếu thay đổi workflow, biến môi trường, endpoint, trạng thái hoặc invariant.

## Lệnh kiểm tra chuẩn

Chạy từ `Notion-facebook-ads-Khai-Hoan-1.1.0/`:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
node --check web_ui/app.js
node --check tests/e2e/planner.spec.js
npm run test:e2e
```

Trong môi trường hiện tại có thể dùng:

```powershell
& 'C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m unittest discover -s tests -p 'test_*.py'
```

Không coi `tests/test_facebook_csv_mapping.py` lệch tên preset legacy là lỗi của tính năng Planner/Meta mới nếu chưa xác minh fixture. Không bỏ qua âm thầm; ghi rõ trong báo cáo test.

## Tiêu chí hoàn thành

- Hành vi đúng yêu cầu và đúng luồng Content → review → Meta `PAUSED`.
- Không lộ secret, không tạo trùng, không mở rộng quyền ngoài yêu cầu.
- Tests liên quan chạy qua hoặc lỗi môi trường được chứng minh rõ.
- Tài liệu phản ánh đúng trạng thái: “đã có”, “fallback”, hay “định hướng”.
