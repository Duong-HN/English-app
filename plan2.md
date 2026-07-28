# Plan 2 — Teacher mode mobile và Teacher Dashboard web

**Trạng thái:** Draft để xem xét
**Quyết định đề xuất:** Giữ kiến trúc hiện tại: mobile là Learner space và điểm truy cập Teacher mode; các thao tác quản lý giáo viên đầy đủ nằm trên Teacher Dashboard web.

## 1. Bối cảnh hiện tại

- Tài khoản đã được duyệt quyền `teacher` có thể chuyển giữa `learner mode` và `teacher mode` trong Cài đặt.
- `TeacherModePage` hiện mới hiển thị thông tin và hướng dẫn dùng Teacher Dashboard; chưa có nút mở URL thật.
- Web portal đã phân quyền theo role:
  - `teacher` → `TeacherDashboard`: tạo lớp, giao bài, xem bài nộp và gửi phản hồi.
  - `admin` → Admin Dashboard: quản trị người dùng, hồ sơ giáo viên, nội dung và nhật ký.
- Flutter chưa có dependency `url_launcher`.
- Stitch project hiện có `Settings - Mode Switching` và `Teacher Dashboard`. Màn hình Teacher Dashboard đang là mobile design, cần chỉnh lại thành web/desktop design nếu không triển khai full teacher CRUD trên mobile.

## 2. Mục tiêu

Khi tài khoản teacher chọn **Teacher mode** trên mobile:

1. Hiển thị một Teacher Overview ngắn gọn.
2. Có nút **Mở Teacher Dashboard**.
3. Nút mở Teacher Dashboard bằng trình duyệt bên ngoài trên điện thoại.
4. Teacher tiếp tục đăng nhập web bằng phiên web riêng.
5. Teacher vẫn có thể chuyển về Learner mode để học và nhận bài như learner.

## 3. Không nằm trong phạm vi MVP

- Không xây lại toàn bộ Teacher Dashboard bằng Flutter mobile.
- Không giao bài, tạo lớp hoặc chấm bài trực tiếp trong Teacher mode mobile.
- Không truyền mobile JWT qua query string hoặc URL.
- Không thay đổi quy trình admin duyệt hồ sơ giáo viên.
- Không thay đổi quyền backend hiện có.

## 4. Luồng người dùng đề xuất

```text
Teacher được duyệt
        ↓
Mobile → Cài đặt → Chế độ sử dụng → Giáo viên
        ↓
Teacher Overview
        ↓
Mở Teacher Dashboard
        ↓
Trình duyệt điện thoại → Web login nếu chưa có phiên
        ↓
Teacher Dashboard: lớp học → giao bài → xem bài nộp → phản hồi
```

Learner flow không thay đổi:

```text
Learner mode → Mobile → nhận bài → làm bài → nộp bài
```

## 5. Thiết kế mobile

### 5.1. Teacher Overview

Giữ giao diện nhẹ, không giả lập full dashboard:

- Tiêu đề: `Không gian giáo viên`.
- Trạng thái: `Bạn đang ở chế độ giáo viên`.
- Tóm tắt quyền: tạo lớp, giao bài, xem bài nộp, phản hồi.
- Nút chính: `Mở Teacher Dashboard`.
- Nút phụ: `Chuyển sang chế độ học viên`.
- Có thể thêm thông báo hồ sơ hoặc trạng thái phiên đăng nhập web.

### 5.2. Mở web dashboard

- Dùng `url_launcher` với `LaunchMode.externalApplication`.
- Không dùng WebView cho MVP để tránh tạo thêm luồng cookie, session và đăng nhập.
- Nếu không mở được URL, hiển thị SnackBar với hướng dẫn thử lại.
- URL dashboard phải lấy từ cấu hình môi trường, không hard-code production URL trong widget.

## 6. Cấu hình URL

Đề xuất dùng `--dart-define`:

```text
TEACHER_DASHBOARD_URL=http://localhost:3000
```

Các môi trường cần có:

- Development: URL local hoặc IP LAN để test trên điện thoại thật.
- Staging: URL dashboard staging.
- Production: URL dashboard production có HTTPS.

Tạo lớp cấu hình, ví dụ:

```text
mobile/lib/src/core/app_config.dart
```

Không đưa API key, JWT hoặc credential vào URL cấu hình.

## 7. Đăng nhập và bảo mật

### MVP — khuyến nghị

- Mobile mở web dashboard.
- Teacher đăng nhập trên web bằng flow hiện có.
- Web tự kiểm tra role `teacher` hoặc `admin` qua endpoint `/me`.
- Nếu tài khoản không còn quyền teacher, web từ chối truy cập.

Ưu điểm: đơn giản, không làm lộ mobile token, không cần thay đổi backend.

### Giai đoạn sau — nếu cần đăng nhập một lần

Triển khai one-time handoff:

1. Mobile gọi backend để tạo mã dùng một lần.
2. Mã có thời hạn ngắn và chỉ dùng được một lần.
3. Mobile mở URL web kèm mã tạm thời.
4. Web đổi mã lấy session cookie của Teacher Dashboard.
5. Không bao giờ đưa access token thật vào URL.

Chỉ làm phần này khi người dùng thực sự cần tránh đăng nhập lại trên web.

## 8. Các thay đổi dự kiến

### Flutter mobile

- Thêm `url_launcher` vào `mobile/pubspec.yaml`.
- Thêm `AppConfig` đọc `TEACHER_DASHBOARD_URL`.
- Cập nhật `TeacherModePage`:
  - thêm nút mở dashboard;
  - xử lý lỗi mở URL;
  - giữ nút chuyển về learner mode.
- Cập nhật copy để nói rõ dashboard mở bằng trình duyệt web.

### Backend

MVP không cần thay đổi backend. Giữ các quy tắc:

- Chỉ teacher đã được duyệt mới có quyền teacher.
- Teacher chỉ thao tác trên lớp do mình sở hữu.
- Admin vẫn giữ quyền quản trị riêng.

### Teacher/admin web

- Giữ route teacher hiện tại.
- Đảm bảo Teacher Dashboard responsive ở kích thước mobile browser.
- Giữ role guard để learner không truy cập portal.
- Kiểm tra deep link và session expiration khi mở từ điện thoại.

### Stitch

- Giữ `Settings - Mode Switching` là mobile screen.
- Đổi `Teacher Dashboard` hiện tại thành bản desktop/web hoặc tạo thêm bản desktop.
- Đổi tên màn hình mobile thành `Teacher Overview` hoặc `Teacher mode handoff`.
- Không thiết kế full CRUD teacher dashboard native trong mobile scope.

## 9. Kiểm thử

### Flutter

- Learner không thấy Teacher mode.
- Teacher đã duyệt thấy nút `Mở Teacher Dashboard`.
- Bấm nút gọi đúng URL cấu hình.
- URL không hợp lệ hiển thị lỗi thân thiện.
- Chuyển về Learner mode vẫn hoạt động.

### Web/backend

- Teacher đăng nhập được Teacher Dashboard.
- Admin vẫn vào Admin Dashboard.
- Learner bị chặn khỏi Teacher Dashboard.
- Teacher không truy cập được lớp của teacher khác.
- Session hết hạn yêu cầu đăng nhập lại.

### Kiểm thử thủ công trên điện thoại

1. Chạy Flutter với URL dashboard development truy cập được từ điện thoại.
2. Đăng nhập tài khoản teacher đã được duyệt.
3. Chuyển sang Teacher mode.
4. Mở dashboard bằng trình duyệt.
5. Đăng nhập web và tạo thử một lớp/giao một bài.
6. Chuyển về Learner mode và kiểm tra bài được giao.

## 10. Tiêu chí hoàn thành

- Teacher mode mobile có nút mở Teacher Dashboard thật.
- Dashboard mở bằng HTTPS ở staging/production.
- Không có token hoặc secret trong URL.
- Teacher và admin đi đúng dashboard theo role.
- Learner vẫn nhận và làm bài trên mobile như trước.
- Stitch phản ánh đúng: mobile Teacher Overview, web Teacher Dashboard.
- Tests Flutter/backend hiện tại vẫn pass.

## 11. Rủi ro và quyết định cần xác nhận

- Cần chốt URL Teacher Dashboard cho development, staging và production.
- Nếu muốn trải nghiệm không cần đăng nhập lại trên web, cần làm one-time handoff ở giai đoạn sau.
- Nếu yêu cầu bắt buộc là teacher phải quản lý đầy đủ trên mobile, plan này không còn phù hợp; khi đó cần một plan riêng cho full mobile teacher workspace.
