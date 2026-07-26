# Cài đặt trên máy khác

1. Giải nén toàn bộ gói phát hành hoặc sao chép thư mục dự án.
2. Nếu dùng bản EXE, mở `NotionFacebookAdsTool.exe`. Nếu dùng mã nguồn, chạy `run_tool.bat` hoặc `run_web.bat`.
3. Sao chép `.env.example` thành `.env`.
4. Điền `NOTION_TOKEN` và `NOTION_DATA_SOURCE_ID` của database cần dùng.
5. File CSV mẫu mặc định là `sample/facebook_ads_template.csv`.
6. Với desktop GUI, có thể vào `Cấu hình` và bấm `Lưu cấu hình`.

Lưu ý:

- Bản EXE tạo bằng `build_exe.ps1` đã đóng gói assets, catalog và CSV mẫu. Khi chạy từ mã nguồn, không đổi tên hoặc xoá các thư mục `assets`, `config`, `sample` và `web_ui`.
- Không gửi file `.env` cho người ngoài nếu trong đó có token.
- File xuất sẽ nằm trong thư mục `exports`.
- Với 10 bài chung một nhóm quảng cáo, hãy chọn cùng `Tên chiến dịch`, `Tên nhóm QC` và `Mẫu đối tượng` trong Notion; file CSV sẽ tạo 10 quảng cáo nằm cùng Campaign/Ad Set.
- Link bài dạng `/posts/pfbid...` sẽ được xuất bằng đúng `Permalink` và tool tự xoá creative cũ của dòng mẫu để tránh import nhầm bài.
