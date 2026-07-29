# Luồng hoạt động LearnMate

Tài liệu này mô tả ba không gian sản phẩm chính:

1. **Mobile Learner** — nơi học viên học, luyện tập và nhận bài từ lớp.
2. **Mobile Teacher** — điểm chuyển chế độ và handoff sang web cho giáo viên đã được duyệt.
3. **Web Dashboard** — không gian làm việc đầy đủ cho teacher và admin.

## Quy ước trạng thái

| Nhãn | Ý nghĩa |
|---|---|
| ✅ Có trong code | Luồng đã có API và/hoặc giao diện hoạt động trong repository. |
| 🟡 Thiết kế đã chốt | Luồng phản ánh thiết kế Figma/định hướng sản phẩm nhưng chưa được triển khai đầy đủ. |
| ⛔ Ngoài MVP | Không triển khai trong mobile MVP hiện tại. |

## Ranh giới vai trò chung

```text
Đăng ký công khai → learner
learner gửi hồ sơ → admin duyệt → teacher
admin được tạo riêng bằng CLI/triển khai

learner  → Mobile Learner
teacher  → Mobile Learner + Mobile Teacher handoff + Teacher Dashboard web
admin    → Admin Dashboard web
```

- Một tài khoản teacher vẫn có thể dùng toàn bộ luồng learner trên mobile.
- Teacher không nhận full teacher CRUD native trên mobile.
- Learner không được truy cập Teacher/Admin Dashboard web.
- Mobile JWT không bao giờ được đưa vào URL mở web dashboard.

---

# 1. Mobile Learner

## 1.1. Điều hướng

### ✅ Điều hướng hiện có trong code

```text
Home      → Tổng quan hôm nay, lộ trình, khóa học, bài lớp
Học       → Trợ lý học tập AI: Đọc / Viết / Nói
Lớp       → Lớp đã tham gia và bài giáo viên giao
Lịch sử   → Lịch sử phân tích AI
Hồ sơ     → Thông tin tài khoản và đăng xuất

Top bar   → Cài đặt và Thông báo
```

Khóa học hiện được mở từ Home qua nút **Mở thư viện khóa học**; từ vựng xuất hiện trong kết quả phân tích và màn chi tiết từ vựng, chưa là tab navigation độc lập.

### 🟡 Điều hướng mục tiêu theo Figma

```text
Trang chủ | Khóa học | Luyện tập | Từ vựng | Cài đặt
```

Quy tắc khi chuyển sang navigation này:

| Tab mục tiêu | Trách nhiệm |
|---|---|
| Trang chủ | Tiến độ, bài tiếp theo, shortcut vào khóa học/luyện tập/từ vựng. |
| Khóa học | Giáo trình A2 → B1, bài học, media, tiến độ từng lesson. |
| Luyện tập | OCR, nhập bài viết, nói bằng transcript và phản hồi AI. |
| Từ vựng | Ôn từ đã lưu/trích xuất từ bài học và phân tích AI. |
| Cài đặt | Tài khoản, không gian học, quyền camera/micro, thông báo và teacher mode. |

Không tạo tab mang tên **OCR** hoặc **LLM**. Người dùng nhìn thấy ngôn ngữ sản phẩm: **Quét bài tiếng Anh** và **Phản hồi AI**.

## 1.2. Đăng ký, đăng nhập và onboarding

### ✅ Luồng hiện có

```text
Mở app
  → Đăng ký hoặc đăng nhập email/password
  → lưu JWT trong secure storage
  → chọn Tự học hoặc Nhập mã mời lớp
  → đặt mục tiêu + thời gian học mỗi ngày
  → làm placement test 20 câu
  → nhận level CEFR
  → tạo lộ trình cá nhân 7 ngày
  → Home
```

Chi tiết:

1. Đăng ký công khai luôn tạo role `learner`.
2. Người dùng có thể chọn **Tự học** hoặc tham gia lớp bằng invite code.
3. Placement test và lộ trình cá nhân thuộc self-study space.
4. Người dùng có thể tiếp tục onboarding nếu bị gián đoạn.

## 1.3. Home và bài học tiếp theo

### ✅ Luồng hiện có

```text
Home
  → Kế hoạch hôm nay
      → Tiếp tục học
          → Học (mở đúng task trong lộ trình)
  → Lộ trình của tôi
      → chọn task → Học
      → Xem toàn bộ lộ trình → Lộ trình cá nhân
  → Giáo trình theo level
      → Mở thư viện khóa học → Khóa học / Lesson
  → Bài từ lớp
      → Mở lớp học → Lớp / Assignment
```

`Tiếp tục học` phải luôn mở hành động tiếp theo, không mở trang thống kê.

## 1.4. Khóa học và lesson

### ✅ Luồng hiện có

```text
Home → Mở thư viện khóa học
  → Chọn course theo level
  → Chọn lesson
  → Đọc / nghe / xem media / làm hoạt động
  → Lưu tiến độ lesson và media
  → Có thể gửi nội dung lesson cho AI phân tích theo ngữ cảnh bài học
```

- Media audio/video có transcript/caption và lưu vị trí nghe/xem.
- Progress lesson thuộc self-study space, không trộn với class space.
- Lesson có thể đưa `lesson_id` vào request AI để backend thêm objective, body và transcript làm ngữ cảnh.

## 1.5. Luyện tập AI: OCR, viết và nói

### ✅ Luồng hiện có

```text
Học / Trợ lý học tập AI
  ├─ Đọc hiểu
  │   ├─ Chụp ảnh OCR hoặc chọn ảnh từ thư viện
  │   ├─ ML Kit nhận dạng chữ Latin ngay trên thiết bị
  │   ├─ Đổ text vào ô có thể chỉnh sửa
  │   ├─ Người học sửa text nếu cần
  │   └─ Phân tích bằng AI
  ├─ Viết
  │   ├─ Nhập bài viết
  │   └─ Phân tích bằng AI
  └─ Nói
      ├─ Bật micro
      ├─ Device STT tạo transcript tiếng Anh
      ├─ Người học kiểm tra/sửa transcript
      └─ Phân tích bằng AI
```

Luồng dữ liệu chung:

```text
Text đã xác nhận
  → POST /api/v1/analyses/{reading|writing|speaking}
  → Backend chọn Mock hoặc Gemini provider
  → validate JSON kết quả
  → lưu analysis theo user + learning space
  → Mobile hiển thị score tham khảo, summary, lỗi ngữ pháp và từ vựng
```

Nguyên tắc:

- OCR chạy trên mobile Android/iOS; không gửi ảnh thô sang LLM trong MVP.
- Gemini key chỉ tồn tại trên backend.
- Speaking hiện đánh giá nội dung transcript, grammar và vocabulary; **không tuyên bố chấm phát âm**.

## 1.6. Từ vựng

### ✅ Luồng hiện có

```text
Kết quả Reading/lesson
  → trích xuất hoặc lookup từ vựng
  → mở vocabulary detail
  → xem nghĩa/ngữ cảnh
  → lưu dữ liệu theo active learning space
```

### 🟡 Luồng mục tiêu theo Figma

```text
Tab Từ vựng
  → danh sách từ cần ôn
  → flashcard / nghĩa / ví dụ
  → đánh dấu đã ôn
  → cập nhật số “Review items” trên Home
```

## 1.7. Tiến độ học tập và Weekly Streak

### ✅ Luồng hiện có

```text
Home → Lộ trình của tôi → Xem toàn bộ lộ trình
  → Lộ trình cá nhân
  → xem tiến độ x/7 ngày
  → xem task, checkpoint và lý do cá nhân hóa
  → tick hoàn thành hoặc hoàn thành qua analysis có context task
  → backend lưu daily_progress
```

### 🟡 Luồng mục tiêu theo Figma

`Weekly Streak` không phải điều kiện để mở tiến độ; đó là một điểm vào phụ của cùng một trang.

```text
Home
  ├─ Card khóa học / 42% Complete
  │   → Tiến độ học tập, focus “Mục tiêu hiện tại”
  ├─ Weekly Streak / 3 Days
  │   → Tiến độ học tập, focus “Hoạt động tuần này”
  └─ Hồ sơ hoặc Cài đặt → Tiến độ học tập
      → xem toàn bộ trang

Tiến độ học tập
  ├─ thời gian học tuần
  ├─ bài đã hoàn thành
  ├─ streak ngày liên tiếp
  ├─ phần trăm khóa học và lộ trình
  ├─ biểu đồ hoạt động tuần
  ├─ chặng đường gần đây
  └─ gợi ý AI dựa trên dữ liệu tuần
```

Hiện repository **chưa có** weekly streak, time tracking theo tuần, chart tuần hoặc trang `LearningProgressPage` riêng. Cần bổ sung API tổng hợp và UI trước khi bật thiết kế này.

## 1.8. Học trong lớp

### ✅ Luồng hiện có

```text
Learner nhận invite code
  → tham gia lớp
  → đổi active learning space sang lớp trong Cài đặt
  → Home hiện bài từ giáo viên
  → Lớp → mở assignment
  → làm bài / nộp bài
  → backend chạy AI analysis khi phù hợp
  → xem teacher feedback
```

- Dữ liệu self-study và lớp được tách theo `learning_space_id`.
- Learner chỉ thấy lớp mình đã tham gia và bài được giao cho lớp đó.

## 1.9. Cài đặt và teacher application

### ✅ Luồng hiện có

```text
Top bar → Cài đặt
  ├─ đổi self-study / lớp đã tham gia
  ├─ quản lý tài khoản
  ├─ xem thông báo
  ├─ learner: gửi hồ sơ trở thành teacher
  └─ teacher đã duyệt: đổi Learner mode / Teacher mode
```

---

# 2. Mobile Teacher

## 2.1. Điều kiện vào Teacher mode

### ✅ Luồng hiện có

```text
Learner
  → gửi teacher application trong Cài đặt
  → admin duyệt trên web
  → role backend đổi thành teacher
  → Cài đặt hiện lựa chọn Teacher mode
  → Teacher Overview trên mobile
```

Nếu tài khoản không có role `teacher`, app không cho chuyển Teacher mode.

## 2.2. Teacher Overview và handoff web

### ✅ Luồng hiện có

```text
Cài đặt → Chế độ sử dụng → Giáo viên
  → Teacher Overview
      → xem mô tả quyền giáo viên
      → Mở Teacher Dashboard
          → mở URL cấu hình bằng browser ngoài app
          → đăng nhập web bằng phiên riêng nếu cần
      → Chuyển sang chế độ học viên
```

`TEACHER_DASHBOARD_URL` được truyền qua `--dart-define`; staging/production phải dùng HTTPS.

## 2.3. Ranh giới Mobile Teacher

| Có trên Mobile Teacher | Không có trên Mobile Teacher MVP |
|---|---|
| Chuyển learner/teacher mode | Tạo lớp native |
| Xem giải thích quyền và handoff | Giao bài native |
| Mở Teacher Dashboard ngoài app | Chấm bài native |
| Quay về học như learner | Quản lý học viên native |

### 🟡 Bổ sung có thể cân nhắc sau MVP

- Badge số bài cần review.
- Link nhanh đến một lớp hoặc submission đang chờ.
- Trạng thái teacher application/role gần nhất.

Các bổ sung này chỉ là overview; full CRUD vẫn ở web.

---

# 3. Web Dashboard

Web dùng một portal nhưng route giao diện và quyền được xác định ở backend theo role.

```text
Web login
  → /me kiểm tra role
  ├─ teacher → Teacher Dashboard
  ├─ admin   → Admin Dashboard
  └─ learner → từ chối truy cập dashboard
```

## 3.1. Teacher Dashboard

### ✅ Luồng hiện có

```text
Teacher mở dashboard web
  → đăng nhập bằng cùng tài khoản teacher
  → Teacher Dashboard
      ├─ tạo / xem lớp
      ├─ lấy hoặc chia sẻ invite code
      ├─ tạo assignment: skill, nội dung, thời lượng, deadline
      ├─ xem danh sách bài nộp
      ├─ xem AI analysis của bài nộp
      └─ gửi teacher feedback

Learner trên mobile
  → thấy assignment
  → nộp bài
  → thấy AI feedback + teacher feedback
```

Ràng buộc quyền:

- Teacher chỉ thao tác lớp do chính mình sở hữu.
- Teacher không biến thành admin chỉ vì đăng nhập cùng portal.
- Session web hết hạn thì đăng nhập lại; mobile session không được dùng để bypass web login.

## 3.2. Admin Dashboard

### ✅ Luồng hiện có

```text
Admin mở dashboard web
  → đăng nhập admin account
  → Admin Dashboard
      ├─ live metrics
      ├─ quản lý người dùng
      ├─ duyệt / từ chối teacher application
      ├─ moderation tài khoản
      ├─ quản lý curriculum và media
      ├─ xem audit logs
      └─ dùng authenticated API Console
```

Ràng buộc quyền:

- Admin API luôn kiểm tra role server-side.
- Các thay đổi quản trị được ghi vào audit log.
- Admin không dùng Mobile Learner như một dashboard quản trị.

## 3.3. Responsive web

### 🟡 Quy tắc thiết kế cần duy trì

```text
Desktop / tablet ngang → sidebar + workspace đầy đủ
Mobile browser         → sidebar thu gọn + bảng có scroll/stack card
```

Teacher Dashboard web có thể được mở từ điện thoại qua Mobile Teacher, nhưng đó vẫn là web dashboard; không tạo bản Flutter CRUD thứ hai.

---

# Ma trận điểm vào chính

| Ý định người dùng | Mobile Learner | Mobile Teacher | Web Dashboard |
|---|---|---|---|
| Bắt đầu bài tiếp theo | Home → Tiếp tục học | Chuyển learner mode → Home | Không áp dụng |
| Quét ảnh tiếng Anh | Học/Luyện tập → Đọc hiểu | Chuyển learner mode | Không áp dụng |
| Xem tiến độ 7 ngày | Home → Lộ trình của tôi | Chuyển learner mode | Admin có báo cáo vận hành, không phải progress cá nhân |
| Weekly Streak / biểu đồ tuần | 🟡 Learning Progress mới | Không áp dụng | Không áp dụng |
| Tạo lớp / giao bài | Không áp dụng | Mở Teacher Dashboard | Teacher Dashboard |
| Duyệt teacher application | Không áp dụng | Không áp dụng | Admin Dashboard |
| Quản lý người dùng / audit | Không áp dụng | Không áp dụng | Admin Dashboard |

# Quy tắc dữ liệu và bảo mật xuyên suốt

```text
Mobile / Web
  → API có Bearer token
  → API xác thực user + role + active learning space
  → Database chỉ trả dữ liệu thuộc user/class được phép
  → AI provider nhận input tối thiểu cần thiết
  → Kết quả được validate trước khi lưu và trả về UI
```

- `self-study` và `class` không trộn progress, analysis hoặc vocabulary.
- API key AI chỉ nằm backend.
- Media lesson cần authentication khi stream.
- Điểm AI là formative/reference, không phải IELTS score chính thức.
- Đánh giá nói hiện không phải chấm phát âm.
