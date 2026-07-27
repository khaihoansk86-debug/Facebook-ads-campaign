# Meta Ad Set copy scheduling (Graph API v25.0)

Ngày xác minh: 2026-07-27.

## Kết luận

- Endpoint `POST /{ad-set-id}/copies` có các tham số sao chép được công bố trong schema SDK chính thức gồm: `campaign_id`, `deep_copy`, `start_time`, `end_time`, `rename_options` và `status_option`.
- Schema của endpoint copy **không liệt kê** `daily_budget` hoặc `lifetime_budget`. Vì vậy không nên dựa vào `/copies` để thay ngân sách ngay trong cùng request.
- Không thể copy một Ad Set đã bắt đầu rồi sửa `start_time` của bản copy bằng request cập nhật tiếp theo. Graph API v25.0 đã từ chối thao tác này với thông báo: `cannot edit start_time if ad set has started`.
- Cách ổn định đã được kiểm chứng để tạo bản sao có lịch trong tương lai là:
  1. đọc cấu hình Ad Set nguồn;
  2. tạo Ad Set mới qua `POST /act_{ad-account-id}/adsets`;
  3. gửi `start_time`, `end_time` và ngân sách Planner ngay trong request tạo;
  4. đặt `status=PAUSED`;
  5. sau đó tạo nhiều quảng cáo vào Ad Set mới.

Với Planner, nên xem Ad Set nguồn là **template cấu hình**, không xem `/copies` là cơ chế tạo chính. Cách tạo trực tiếp cho phép lịch và ngân sách được xác định nguyên tử ngay từ đầu, tránh bản copy bị Meta xem là đã bắt đầu trước khi có thể cập nhật.

## Tham số của `POST /{ad-set-id}/copies`

Schema được sinh tự động trong Meta Python Business SDK liệt kê:

| Tham số | Kiểu | Ý nghĩa |
|---|---|---|
| `campaign_id` | string | Campaign đích |
| `deep_copy` | boolean | Sao chép sâu các đối tượng con |
| `start_time` | datetime | Thời gian bắt đầu của bản sao |
| `end_time` | datetime | Thời gian kết thúc của bản sao |
| `rename_options` | object | Quy tắc đổi tên khi sao chép |
| `status_option` | enum | Cách xử lý trạng thái của bản sao |

`daily_budget` và `lifetime_budget` không nằm trong danh sách tham số của edge `copies`. Đây là lý do ngân sách cần được kế thừa rồi cập nhật khi còn hợp lệ, hoặc tốt hơn là gửi trong request tạo Ad Set mới.

Nguồn chính thức:

- [Meta Marketing API reference — Ad Campaign Copies](https://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/)
- [Meta Python Business SDK — generated `AdSet.api_create_copy` schema](https://github.com/facebook/facebook-python-business-sdk/blob/main/facebook_business/adobjects/adset.py)

> Lưu ý tên đối tượng trong reference/SDK: Meta dùng tên nội bộ `AdCampaign` cho Ad Set ở một số đường dẫn tài liệu cũ; Graph edge thực tế vẫn là `/{ad-set-id}/copies`.

## Bằng chứng runtime Graph API v25.0

Các request sau được chạy trực tiếp với tài khoản quảng cáo thử nghiệm trong vòng hồi quy ngày 2026-07-27:

1. Một Ad Set đang/đã bắt đầu được sao chép.
2. Request tiếp theo cố đặt lại `start_time` cho bản sao bị Graph API từ chối với lỗi: `cannot edit start_time if ad set has started`.
3. `POST /act_{ad-account-id}/adsets` với cấu hình nguồn, `start_time` tương lai, `end_time`, ngân sách và `status=PAUSED` đã tạo thành công.

Đây là bằng chứng first-party runtime từ chính Graph API v25.0. Không ghi access token hoặc dữ liệu xác thực vào tài liệu này.

## Hàm ý cho nghiệp vụ gom nhiều quảng cáo

Một link bài viết có thể sinh nhiều format quảng cáo trong một lần, nhưng cấu trúc nên là:

```text
1 campaign PAUSED
└── N ad sets PAUSED (mỗi format/audience/placement cần cấu hình khác nhau)
    └── M ads PAUSED dùng cùng object_story_id khi format hỗ trợ bài có sẵn
```

Mỗi Ad Set phải được tạo trực tiếp với lịch và ngân sách của Planner. Sau khi toàn bộ Ad Set thành công, hệ thống mới tạo các Ad bên dưới. Ledger/idempotency phải lưu ID theo từng Campaign, Ad Set và Ad để retry không tạo trùng.

## Giới hạn xác minh tài liệu

Trong phiên làm việc này, trang `developers.facebook.com` và raw GitHub không truy cập được từ môi trường thực thi. Vì vậy không thể lưu snapshot HTML của tài liệu theo đúng phiên bản v25.0. Danh sách tham số ở trên dựa trên schema công khai do Meta sinh trong SDK chính thức; quyết định triển khai dựa thêm vào phản hồi trực tiếp của Graph API v25.0 đã nêu ở phần runtime.

