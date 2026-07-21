# LearnMate Admin

Web quản trị dành cho đội vận hành LearnMate AI. Ứng dụng dùng API backend thật,
không chứa dữ liệu dashboard giả lập.

## Chức năng

- Đăng nhập bằng JWT và chặn tài khoản không có role `admin`.
- Tổng quan người dùng, bài phân tích và xu hướng 7 ngày.
- Tìm kiếm, phân trang, đổi vai trò và khóa/mở tài khoản.
- Xem chi tiết, lọc và xóa bài phân tích.
- Xem nhật ký thao tác quản trị.
- Theo dõi trạng thái backend định kỳ.
- Cấu hình URL backend ngay trên màn hình đăng nhập.
- API Console kiểu Postman: preset endpoint, JWT tự động, status/time/size,
  response body/header, lịch sử an toàn và xuất lệnh cURL.

## Chạy cục bộ

Yêu cầu Node.js `>=22.13.0` và backend LearnMate đang chạy.

```bash
npm install
npm run dev
```

Mặc định web kết nối `http://127.0.0.1:8000`. Có thể đặt URL khác:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com npm run dev
```

Trên PowerShell:

```powershell
$env:NEXT_PUBLIC_API_BASE_URL="https://api.example.com"
$env:NEXT_PUBLIC_SITE_URL="https://admin.example.com"
npm run dev
```

Tạo tài khoản quản trị từ thư mục `backend`:

```powershell
$env:ADMIN_PASSWORD="mot-mat-khau-manh"
python -m app.cli create-admin --email admin@example.com --display-name "System Admin"
```

## Kiểm tra

```bash
npm run lint
npm test
```

`npm test` tạo bản build Cloudflare Worker rồi kiểm tra HTML render phía server.
Phiên JWT chỉ lưu trong `sessionStorage` và tự mất khi đóng tab trình duyệt.

## Docker

Từ thư mục gốc dự án:

```powershell
docker compose up --build admin
```

Image production chạy bằng user Node không đặc quyền, phục vụ bản build trên cổng
`3000` và có health check HTTP. Đặt `NEXT_PUBLIC_API_BASE_URL` thành URL HTTPS mà
trình duyệt người quản trị có thể truy cập; không dùng hostname nội bộ Docker cho
biến này.
