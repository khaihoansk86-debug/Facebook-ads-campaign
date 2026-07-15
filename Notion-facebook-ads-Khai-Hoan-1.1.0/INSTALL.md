# Cài đặt trên máy khác

1. Giải nén toàn bộ thư mục `Notion Facebook Ads Khai Hoan`.
2. Mở file `Notion - Facebook Ads Khai Hoan.exe`.
3. Vào `Cấu hình`, điền `Notion token` nếu chưa có.
4. Giữ nguyên `Notion data source ID` nếu vẫn dùng database Khải Hoàn hiện tại.
5. File CSV mẫu đã nằm sẵn trong thư mục `sample/facebook_ads_template.csv`.
6. Bấm `Lưu cấu hình`.

Lưu ý:

- Không đổi tên hoặc xoá thư mục `sample`, vì tool cần file CSV mẫu để clone cấu hình Facebook Ads cũ.
- Không gửi file `.env` cho người ngoài nếu trong đó có token.
- File xuất sẽ nằm trong thư mục `exports`.
- Với 10 bài chung một nhóm quảng cáo, hãy chọn cùng `Tên chiến dịch`, `Tên nhóm QC` và `Mẫu đối tượng` trong Notion; file CSV sẽ tạo 10 quảng cáo nằm cùng Campaign/Ad Set.
- Link bài dạng `/posts/pfbid...` sẽ được xuất bằng đúng `Permalink` và tool tự xoá creative cũ của dòng mẫu để tránh import nhầm bài.
