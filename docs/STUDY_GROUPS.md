# Nhóm học tập cộng tác

Mô hình nhóm học tập thay thế vai trò “Teacher” trong luồng cộng tác chính: mọi tài khoản learner/teacher đều có thể tạo nhóm, mời bạn bè bằng mã nhóm, tạo bài tập và tham gia peer review. Role `teacher`, lớp cũ và Teacher Dashboard vẫn được giữ để tương thích với dữ liệu và demo hiện có.

## Luồng người dùng

```text
Người dùng đăng nhập
  → Tạo nhóm hoặc nhập mã mời
  → Thành viên tạo bài tập chung
  → Mọi người nộp bài
  → Chấm peer review cho bài của bạn khác
  → Xem điểm và bảng xếp hạng theo cấp độ
```

## API chính

- `POST /api/v1/study-groups` — tạo nhóm; người tạo là owner và nhận mã mời.
- `GET /api/v1/study-groups` — danh sách nhóm mà người dùng sở hữu hoặc đã tham gia.
- `POST /api/v1/study-groups/join` — tham gia nhóm bằng `invite_code`.
- `GET /api/v1/study-groups/{id}/members` — danh sách thành viên trong nhóm.
- `POST /api/v1/study-groups/{id}/assignments` — bất kỳ thành viên nào cũng có thể tạo bài tập.
- `GET /api/v1/study-groups/{id}/assignments` — bài tập chung và trạng thái nộp của người dùng hiện tại.
- `GET /api/v1/study-groups/{id}/assignments/{assignment_id}/peer-reviews` — hàng đợi bài của bạn học cần chấm.
- `POST /api/v1/submissions/{submission_id}/peer-reviews` — gửi hoặc cập nhật một peer review cho mỗi bài.
- `GET /api/v1/submissions/{submission_id}/peer-reviews` — tác giả xem các peer review nhận được.
- `GET /api/v1/leaderboards?level=B1` — bảng xếp hạng toàn hệ thống theo cấp độ.
- `GET /api/v1/study-groups/{id}/leaderboard` — bảng xếp hạng trong nhóm.

Điểm xếp hạng hiện tại được tính minh bạch theo công thức: hoàn thành một bài = 10 điểm, thực hiện một peer review = 5 điểm. Điểm trung bình nhận được được hiển thị riêng để khuyến khích chất lượng phản hồi nhưng chưa cộng vào điểm xếp hạng.

## Phân quyền

- `learner` và `teacher` đều được dùng nhóm học tập.
- Chỉ thành viên nhóm mới xem nhóm, bài tập, hàng đợi review và leaderboard của nhóm.
- Người dùng không được peer review bài của chính mình.
- Mỗi reviewer chỉ có một review cho một submission; gửi lại sẽ cập nhật review đó.
- Leaderboard theo cấp độ dùng `User.level` hiện có (`A1`, `A2`, `B1`, `B2`, `C1`).
