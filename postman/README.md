# LearnMate API workspace

Thư mục này chứa bộ request Postman có thể đưa vào Git và dùng chung mà không
lưu JWT, mật khẩu quản trị hay API key.

## Chuẩn bị

Từ thư mục gốc dự án:

```powershell
docker compose up -d --build --wait
```

Nếu chưa có tài khoản quản trị:

```powershell
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
docker compose exec -e ADMIN_PASSWORD api python -m app.cli create-admin --email admin@example.com --display-name "LearnMate Admin"
Remove-Item Env:ADMIN_PASSWORD
```

## Dùng trong Postman

1. Import `collections/LearnMate AI API.postman_collection.json`.
2. Import và chọn `environments/LearnMate Local.postman_environment.json`.
3. Điền `learnerPassword`, `teacherPassword` và `adminPassword` trong Current value của máy bạn.
4. Chạy `Đăng ký học viên` nếu cần, sau đó chạy `Đăng nhập học viên`.
5. Request đăng nhập tự lưu JWT vào môi trường; các request tiếp theo tự gắn
   Bearer token.
6. Đăng ký tài khoản giáo viên như một learner, rồi dùng màn hình người dùng của admin để đổi role thành `teacher`.
7. Chạy `Đăng nhập giáo viên` trước nhóm Classrooms và `Đăng nhập quản trị` trước nhóm Administration.
8. Chạy nhóm Classrooms theo đúng thứ tự. Nhóm này tự tạo một bài viết bằng learner để lấy `analysisId`, sau đó tạo lớp, learner xin tham gia, teacher duyệt, giao bài, learner nộp và teacher xem bài nộp.

Không export Current values có chứa mật khẩu hoặc token rồi commit lại. Swagger
UI vẫn có tại <http://localhost:8000/docs>; API Console tích hợp trong dashboard
có tại <http://localhost:3000>.
