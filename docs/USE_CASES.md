# LearnMate AI — Use Case Specification

Tài liệu này mô tả 13 use case của LearnMate AI, dựa trên thiết kế Figma Learnmate AI và các luồng hiện có trong repository.

## Actors

- **Learner:** học viên.
- **Teacher:** giáo viên đã được admin duyệt.
- **Admin:** quản trị viên.
- **AI Service:** dịch vụ phân tích nội dung và tạo lộ trình.
- **Device Services:** camera, gallery, microphone, OCR và speech-to-text.

## Trạng thái triển khai

- **Đã có:** đã có API và/hoặc giao diện hoạt động trong project.
- **Một phần:** đã có nền tảng nhưng chưa khớp đầy đủ với thiết kế Figma.
- **Mục tiêu Figma:** có trong thiết kế, cần hoàn thiện thêm trong product flow.

---

## UC01 — Đăng ký và đăng nhập

**Actor:** Learner, Teacher, Admin

**Mục tiêu:** Cho phép người dùng truy cập hệ thống.

**Tiền điều kiện:**

- Người dùng đã mở mobile app hoặc Teacher/Admin Dashboard.
- Có kết nối tới backend.

**Luồng chính:**

1. Người dùng chọn `Đăng ký` hoặc `Đăng nhập`.
2. Nhập email và mật khẩu.
3. Hệ thống gửi thông tin tới backend.
4. Backend kiểm tra thông tin.
5. Nếu hợp lệ, hệ thống tạo JWT.
6. Ứng dụng lưu token trong secure storage.
7. Hệ thống kiểm tra role và trạng thái onboarding.
8. Điều hướng:
   - Learner mới → UC02.
   - Learner đã hoàn tất onboarding → UC03.
   - Teacher → learner mode hoặc UC12.
   - Admin → Admin Dashboard.

**Luồng ngoại lệ:**

- Email đã tồn tại.
- Sai email hoặc mật khẩu.
- Token hết hạn.
- Backend không phản hồi.

**Hậu điều kiện:** Người dùng đăng nhập thành công và phiên đăng nhập được lưu an toàn.

**Trạng thái:** Đã có.

---

## UC02 — Onboarding và Placement Test

**Actor:** Learner mới

**Mục tiêu:** Thu thập mục tiêu học tập và xác định trình độ ban đầu.

**Tiền điều kiện:** Người dùng đã đăng nhập nhưng chưa hoàn tất onboarding.

**Luồng chính:**

1. Người dùng chọn `Tự học`.
2. Chọn mục tiêu: IELTS, giao tiếp, du học hoặc công việc.
3. Chọn thời gian học mỗi ngày.
4. Hệ thống hiển thị Placement Test gồm 20 câu.
5. Người dùng trả lời từng câu hỏi.
6. Người dùng chọn `Nộp bài`.
7. Backend chấm điểm.
8. Hệ thống hiển thị tổng số câu đúng, trình độ CEFR ước lượng và điểm theo kỹ năng.
9. Người dùng chọn `Tạo lộ trình của tôi`.
10. Backend tạo learning path 7 ngày.
11. Điều hướng đến Home Dashboard.

**Luồng thay thế:**

- Người dùng chọn `Tham gia lớp`.
- Nhập invite code.
- Nếu mã hợp lệ, người dùng tham gia class space và nhận bài từ giáo viên.
- Class mode có thể đi thẳng vào bài được giao mà không cần tạo self-study path.

**Luồng ngoại lệ:**

- Chưa trả lời đủ 20 câu.
- Invite code không hợp lệ.
- Tạo lộ trình thất bại.
- Người dùng thoát giữa chừng.

**Hậu điều kiện:** Learner có level và learning path tương ứng với learning space.

**Lưu ý:** Điểm placement chỉ là điểm tham khảo, không phải chứng chỉ IELTS/CEFR chính thức.

**Trạng thái:** Đã có.

---

## UC03 — Xem Home Dashboard

**Actor:** Learner

**Mục tiêu:** Hiển thị tình trạng học tập và hành động tiếp theo.

**Tiền điều kiện:** Người dùng đã đăng nhập và có active learning space.

**Luồng chính:**

1. Người dùng mở trang chủ.
2. Hệ thống hiển thị lời chào.
3. Hiển thị khóa học hiện tại, ví dụ `English A2 → B1`.
4. Hiển thị phần trăm hoàn thành và số bài học còn lại.
5. Hiển thị bài học tiếp theo.
6. Hiển thị shortcut tới khóa học, luyện tập AI và từ vựng.
7. Nếu đang ở class space, hiển thị bài tập lớp.
8. Người dùng chọn `Tiếp tục học`.
9. Hệ thống mở đúng task tiếp theo.

**Luồng thay thế:**

- Mở toàn bộ learning path.
- Mở khóa học.
- Mở bài tập lớp.
- Chuyển giữa self-study space và class space.

**Luồng ngoại lệ:**

- Không tải được dữ liệu Home.
- Không có learning path.
- Active space không còn quyền truy cập.

**Hậu điều kiện:** Người dùng được chuyển đến use case tương ứng.

**Trạng thái:** Đã có, nhưng navigation hiện tại chưa giống hoàn toàn Figma.

---

## UC04 — Xem khóa học và Curriculum

**Actor:** Learner

**Mục tiêu:** Cho phép người học duyệt khóa học, unit và lesson.

**Tiền điều kiện:** Learner đang ở self-study space và curriculum tồn tại.

**Luồng chính:**

1. Người dùng chọn `Khóa học`.
2. Hệ thống hiển thị khóa học hiện tại.
3. Hiển thị level và phần trăm hoàn thành.
4. Hiển thị danh sách unit.
5. Hiển thị các lesson trong từng unit.
6. Người dùng chọn một lesson.
7. Hệ thống mở Lesson Detail.

**Ví dụ theo Figma:**

- Unit 1: Plans, routines and healthy choices.
- Talking about daily routines.
- Making healthy choices.
- Future plans and intentions.

**Luồng ngoại lệ:**

- Curriculum chưa được tải.
- Không có lesson.
- Lesson không thuộc learning space hiện tại.

**Hậu điều kiện:** Người dùng mở được lesson đã chọn.

**Trạng thái:** Đã có.

---

## UC05 — Học lesson và đánh dấu hoàn thành

**Actor:** Learner

**Mục tiêu:** Cho phép người học hoàn thành một bài học.

**Tiền điều kiện:** Người dùng đã mở lesson và lesson có nội dung hợp lệ.

**Luồng chính:**

1. Hệ thống hiển thị tiêu đề và mục tiêu bài học.
2. Người dùng đọc nội dung lesson.
3. Người dùng xem video hoặc nghe audio.
4. Hệ thống lưu vị trí media đang học.
5. Người dùng mở transcript/captions.
6. Người dùng xem key vocabulary.
7. Người dùng thực hiện activity hoặc Quick Quiz.
8. Người dùng có thể gửi nội dung lesson cho AI.
9. Người dùng chọn `Đánh dấu hoàn thành`.
10. Backend lưu lesson progress.
11. Home Dashboard được cập nhật.

**Luồng ngoại lệ:**

- Media không tải được.
- Mất kết nối mạng.
- Không lưu được media progress.
- AI analysis thất bại nhưng lesson vẫn có thể hoàn thành.

**Hậu điều kiện:** Lesson có trạng thái completed và tiến độ khóa học được cập nhật.

**Trạng thái:** Đã có.

---

## UC06 — Luyện tập và nhận phản hồi từ AI

**Actor:** Learner, AI Service, Camera/Gallery, Microphone/STT

**Mục tiêu:** Phân tích bài đọc, bài viết hoặc transcript nói.

**Tiền điều kiện:** Người dùng đã đăng nhập và có nội dung cần phân tích.

**Luồng chính:**

1. Người dùng mở `Luyện tập AI`.
2. Chọn Reading, Writing hoặc Speaking.
3. Với Reading, người dùng chụp/chọn ảnh, chạy OCR và chỉnh sửa text.
4. Với Writing, người dùng nhập bài viết.
5. Với Speaking, người dùng bật microphone, tạo transcript bằng STT và chỉnh sửa transcript.
6. Người dùng chọn `Nhờ AI nhận xét`.
7. Backend nhận nội dung đã xác nhận.
8. AI trả về score tham khảo, summary, điểm mạnh, lỗi ngữ pháp, từ vựng và gợi ý cải thiện.
9. Hệ thống lưu kết quả.
10. Người dùng xem kết quả hoặc chọn `Làm lại`.

**Luồng ngoại lệ:**

- Người dùng từ chối quyền camera hoặc microphone.
- OCR không nhận dạng được nội dung.
- Speech-to-text không hoạt động.
- Nội dung quá ngắn.
- AI Service không phản hồi.

**Hậu điều kiện:** Analysis được lưu theo user và learning space; kết quả có thể xem lại trong lịch sử.

**Lưu ý:** Speaking hiện đánh giá transcript, grammar và vocabulary; chưa đánh giá phát âm thực tế.

**Trạng thái:** Đã có.

---

## UC07 — Tra cứu và lưu từ vựng

**Actor:** Learner, Dictionary Service

**Mục tiêu:** Tra cứu nghĩa và lưu từ vựng cần học.

**Tiền điều kiện:** Người dùng có một từ cần tra và đang sử dụng active learning space.

**Luồng chính:**

1. Người dùng chọn từ trong lesson hoặc kết quả AI.
2. Hệ thống gọi vocabulary lookup.
3. Hiển thị nghĩa, từ loại, ví dụ và ngữ cảnh.
4. Người dùng chọn lưu từ.
5. Hệ thống lưu từ vào vocabulary list.
6. Từ được gắn với learning space hiện tại.

**Luồng thay thế:**

- Nhập trực tiếp từ cần tìm.
- Lưu từ trực tiếp từ AI analysis.

**Luồng ngoại lệ:**

- Không tìm thấy từ.
- Dictionary Service không phản hồi.
- Từ đã tồn tại.

**Hậu điều kiện:** Vocabulary item được lưu và có thể mở Vocabulary Detail.

**Trạng thái:** Đã có.

---

## UC08 — Ôn tập từ vựng bằng flashcard

**Actor:** Learner

**Mục tiêu:** Giúp người học ôn các từ đã lưu.

**Tiền điều kiện:** Người dùng có vocabulary items và mở Vocabulary tab.

**Luồng chính:**

1. Người dùng chọn tab `Từ vựng`.
2. Hệ thống hiển thị số lượng từ cần ôn trong ngày.
3. Người dùng mở một flashcard.
4. Xem từ, nghĩa và ví dụ.
5. Người dùng lật hoặc mở chi tiết card.
6. Chọn `Đã ôn`.
7. Hệ thống cập nhật trạng thái review.
8. Số lượng `Review items` trên Home được cập nhật.

**Luồng thay thế:**

- Bỏ qua từ.
- Mở Vocabulary Detail.
- Xóa từ khỏi danh sách.

**Luồng ngoại lệ:**

- Không có từ cần ôn.
- Vocabulary list không tải được.

**Hậu điều kiện:** Review count và trạng thái ôn từ được cập nhật.

**Trạng thái:** Mục tiêu Figma; code hiện đã hỗ trợ lookup/save nhưng chưa hoàn chỉnh thành tab flashcard riêng.

---

## UC09 — Xem tiến độ học tập

**Actor:** Learner

**Mục tiêu:** Theo dõi quá trình học theo tuần và theo mục tiêu.

**Tiền điều kiện:** Người dùng đã có hoạt động học và hệ thống có dữ liệu progress.

**Luồng chính:**

1. Người dùng mở `Tiến độ học tập`.
2. Hệ thống hiển thị thời gian học trong tuần.
3. Hiển thị số bài đã hoàn thành.
4. Hiển thị số ngày học liên tiếp.
5. Hiển thị phần trăm hoàn thành mục tiêu hiện tại.
6. Hiển thị biểu đồ hoạt động trong tuần.
7. Hiển thị milestone gần đây.
8. Hiển thị gợi ý học từ LearnMate AI.
9. Người dùng chọn `Xem chi tiết lộ trình`.
10. Hệ thống mở learning path tương ứng.

**Ví dụ theo Figma:**

- 3 giờ học mỗi tuần.
- 12 bài học đã hoàn thành.
- 3 ngày liên tiếp.
- 42% tiến độ A2 → B1.
- Unit 3 đã hoàn thành.
- Unit 4 là bài học tiếp theo.

**Luồng ngoại lệ:**

- Chưa có dữ liệu học tập.
- Không tải được biểu đồ.
- Không có gợi ý AI.

**Hậu điều kiện:** Không thay đổi dữ liệu; đây là use case xem báo cáo.

**Trạng thái:** Một phần. Learning path và daily progress đã có; weekly streak, chart và trang progress riêng chưa đầy đủ.

---

## UC10 — Tham gia lớp và nộp assignment

**Actor:** Learner, Teacher, AI Service

**Mục tiêu:** Cho phép học viên học theo lớp và nộp bài được giao.

**Tiền điều kiện:** Learner có invite code hợp lệ hoặc đã là thành viên lớp.

**Luồng chính:**

1. Người dùng nhập invite code.
2. Backend kiểm tra mã.
3. Người dùng được thêm vào class space.
4. Người dùng mở danh sách lớp.
5. Chọn một lớp.
6. Xem các assignment.
7. Chọn assignment cần làm.
8. Đọc yêu cầu và deadline.
9. Nhập câu trả lời.
10. Chọn `Nộp bài`.
11. Backend lưu submission.
12. AI phân tích nếu assignment yêu cầu.
13. Người dùng xem AI feedback.
14. Sau khi giáo viên chấm, người dùng xem teacher feedback.

**Luồng ngoại lệ:**

- Invite code không hợp lệ.
- Không có quyền truy cập lớp.
- Assignment đã hết hạn.
- Submission không hợp lệ.
- Không thể tải feedback.

**Hậu điều kiện:** Assignment submission được lưu và giáo viên có thể xem, phản hồi bài làm.

**Trạng thái:** Đã có.

---

## UC11 — Quản lý cài đặt và hồ sơ

**Actor:** Learner, Teacher

**Mục tiêu:** Quản lý tài khoản, learning space và chế độ sử dụng.

**Tiền điều kiện:** Người dùng đã đăng nhập.

**Luồng chính:**

1. Người dùng mở `Cài đặt`.
2. Xem thông tin tài khoản.
3. Xem các learning space đã tham gia.
4. Chọn active space: tự học hoặc một lớp đã tham gia.
5. Xem hoặc quản lý nhắc lịch học.
6. Learner có thể gửi teacher application.
7. Teacher đã được duyệt có thể chọn Learner mode hoặc Teacher mode.
8. Người dùng có thể đăng xuất.

**Luồng ngoại lệ:**

- Không tải được learning spaces.
- Không thể chuyển active space.
- Teacher application đang chờ duyệt.
- Người dùng không đủ quyền chuyển Teacher mode.

**Hậu điều kiện:** Active space, chế độ sử dụng hoặc phiên đăng nhập được cập nhật.

**Trạng thái:** Đã có.

---

## UC12 — Teacher Mode và Teacher Dashboard

**Actor:** Teacher

**Mục tiêu:** Cho phép giáo viên quản lý lớp thông qua web dashboard.

**Tiền điều kiện:**

- Tài khoản đã được admin duyệt role teacher.
- Teacher Dashboard URL hợp lệ.

**Luồng chính:**

1. Teacher mở `Cài đặt`.
2. Chọn `Giáo viên`.
3. Hệ thống hiển thị Teacher Overview.
4. Teacher chọn `Mở Teacher Dashboard`.
5. Ứng dụng mở dashboard bằng trình duyệt ngoài.
6. Teacher đăng nhập web session.
7. Teacher có thể tạo lớp, lấy invite code, xem thành viên và tạo assignment.
8. Teacher xem bài nộp và AI analysis.
9. Teacher gửi teacher feedback.
10. Teacher có thể quay lại mobile learner mode.

**Luồng ngoại lệ:**

- Learner chưa được duyệt teacher.
- Teacher Dashboard URL sai.
- Web session hết hạn.
- Teacher không có quyền với lớp khác.

**Hậu điều kiện:** Lớp, assignment và feedback được lưu trên backend.

**Trạng thái:** Đã có.

---

## UC13 — Quản trị hệ thống

**Actor:** Admin

**Mục tiêu:** Quản lý người dùng, nội dung và hoạt động hệ thống.

**Tiền điều kiện:** Admin đăng nhập Admin Dashboard bằng tài khoản có role admin.

**Luồng chính:**

1. Admin đăng nhập web dashboard.
2. Backend kiểm tra role.
3. Admin xem live metrics.
4. Quản lý danh sách user.
5. Duyệt hoặc từ chối teacher application.
6. Moderation tài khoản.
7. Quản lý curriculum và lesson media.
8. Xem AI analyses và learning paths.
9. Xem audit logs.
10. Sử dụng authenticated API Console khi cần.

**Luồng ngoại lệ:**

- Người dùng không có quyền admin.
- Không thể vô hiệu hóa admin cuối cùng.
- Không thể thay đổi teacher đang sở hữu lớp.
- Thao tác quản trị thất bại.
- API Console hết phiên đăng nhập.

**Hậu điều kiện:** Thay đổi quản trị được lưu và các thao tác quan trọng được ghi vào audit log.

**Trạng thái:** Đã có trên Web Dashboard; không thuộc mobile Figma chính.

---

## Quan hệ giữa các Use Case

```text
UC01 Đăng nhập
  └── UC02 Onboarding + Placement Test
        └── UC03 Home Dashboard
              ├── UC04 Curriculum
              │     └── UC05 Học lesson
              │           └── UC06 Luyện tập AI
              │                 └── UC07 Lưu từ vựng
              ├── UC08 Ôn từ vựng
              ├── UC09 Xem tiến độ
              └── UC10 Học trong lớp

UC11 Cài đặt
  └── UC12 Teacher Mode

UC13 Admin
  ├── Duyệt Teacher
  ├── Quản lý Curriculum
  └── Quản lý User và Audit Log
```

## Tài liệu tham chiếu

- [User flows](USER_FLOWS.md)
- [Mobile home flow](../mobile/lib/src/features/home/home_page.dart)
- [Onboarding](../mobile/lib/src/features/onboarding/onboarding_page.dart)
- [Curriculum and lesson](../mobile/lib/src/features/content/curriculum_page.dart)
- [AI analysis API](../backend/app/routers/analyses.py)
- [Placement test API](../backend/app/routers/placement.py)
