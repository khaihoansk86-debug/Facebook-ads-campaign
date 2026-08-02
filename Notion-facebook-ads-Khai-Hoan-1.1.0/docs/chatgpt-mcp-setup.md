# ChatGPT MCP cho Khải Hoàn Ads Planner

ChatGPT là giao diện hội thoại. Dự án không xây thêm chat UI riêng. MCP server chạy trên máy Windows và chỉ cung cấp dữ liệu cùng các hành động lập kế hoạch an toàn.

## Phạm vi an toàn

MCP hiện hỗ trợ:

- đọc catalog Planner;
- lấy bài Page theo khoảng ngày;
- đọc tài sản đối tượng Meta;
- đọc/lưu preset đối tượng và vị trí;
- kiểm tra cây kế hoạch;
- gửi kế hoạch vào trạng thái `PENDING_REVIEW`;
- xem trạng thái và chi tiết kế hoạch duyệt.

MCP không cung cấp công cụ duyệt, publish, kích hoạt hoặc xóa Campaign/Ad set/Ads. Các bước đó tiếp tục thực hiện trong web Planner với quyền IT/Ads Operator.

## Kiểm tra MCP tại máy Windows

```powershell
& 'C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe' mcp_server.py --self-test
```

MCP dùng JSON-RPC qua `stdio`. Không mở thêm cổng mạng.

## Kết nối bằng Secure MCP Tunnel

Tài liệu chính thức: <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>

1. Đăng nhập OpenAI Platform bằng tổ chức sẽ quản lý tunnel.
2. Mở <https://platform.openai.com/settings/organization/tunnels>.
3. Tạo tunnel và liên kết tunnel với ChatGPT workspace cần sử dụng.
4. Tải `tunnel-client` từ trang cài đặt hoặc bản phát hành chính thức.
5. Trên máy Windows, khởi tạo profile `stdio` bằng `tunnel_id` thật:

```powershell
$khTunnelClient = 'C:\Users\Admin\AppData\Local\KhaiHoanAds\tunnel-client\v0.0.10\tunnel-client.exe'
$khPython = 'C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$khMcpServer = 'D:\code facebook ads khaihoan\Notion-facebook-ads-Khai-Hoan-1.1.0\mcp_server.py'
$khMcpCommand = '"{0}" "{1}"' -f $khPython, $khMcpServer

& $khTunnelClient init `
  --sample sample_mcp_stdio_local `
  --profile khai-hoan-ads `
  --tunnel-id tunnel_THAY_BANG_ID_THAT `
  --mcp-command $khMcpCommand

& $khTunnelClient doctor --profile khai-hoan-ads --explain
& $khTunnelClient run --profile khai-hoan-ads
```

`tunnel-client` v0.0.10 đã được cài và kiểm tra SHA-256 tại đường dẫn trên. Runtime API key của tunnel được cung cấp qua biến môi trường `CONTROL_PLANE_API_KEY` trong phiên chạy hoặc kho bí mật của Windows; không ghi key vào repository hoặc chia sẻ cho nhân viên.

## Tạo ứng dụng trong ChatGPT

Tài liệu chính thức: <https://developers.openai.com/api/docs/guides/developer-mode>

1. Trong ChatGPT web, mở **Settings → Security and login** và bật **Developer mode**.
2. Mở <https://chatgpt.com/plugins> và chọn nút tạo app.
3. Đặt tên `Khải Hoàn Ads Planner`.
4. Chọn **Tunnel** rồi chọn tunnel đã liên kết với workspace.
5. Kiểm tra danh sách tool. Không tiếp tục nếu xuất hiện tool duyệt, publish, kích hoạt hoặc xóa quảng cáo.
6. Trong cuộc trò chuyện, chọn app `Khải Hoàn Ads Planner` từ menu công cụ.

## Hướng dẫn đặt trong ChatGPT Project

```text
Bạn là trợ lý lập kế hoạch quảng cáo Khải Hoàn.
Luôn gọi get_planner_catalog trước khi đề xuất cấu hình mới.
Khi dùng Đối tượng tùy chỉnh hoặc Đối tượng tương tự, gọi get_meta_audience_assets để lấy đúng ID.
Giải thích ngắn lý do chọn đối tượng và placement.
Chỉ gọi create_audience_preset hoặc create_placement_preset sau khi người dùng xác nhận.
Luôn gọi preview_planner_plan trước submit_planner_review.
Không được duyệt, publish, kích hoạt hoặc xóa quảng cáo.
Các bước tạo trên Meta phải chuyển sang web Planner cho IT/Ads Operator.
```

## Vận hành

- `tunnel-client run --profile khai-hoan-ads` phải luôn chạy trên máy Windows.
- Nhật ký các thao tác ghi nằm mặc định tại `.web_state/mcp_audit.jsonl`.
- Không gửi Meta token, khóa người duyệt hoặc runtime API key vào ChatGPT.
- Mỗi thao tác ghi yêu cầu trường tên nhân viên và ChatGPT Developer mode sẽ hiển thị xác nhận cho write tool.
- Dùng ChatGPT Business workspace nếu triển khai cho nhiều nhân viên để quản lý app và quyền ở một nơi.
