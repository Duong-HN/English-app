# Phạm vi và giới hạn của đồ án LearnMate

## 1. Mục đích của tài liệu

Tài liệu này chốt phạm vi chính thức của LearnMate để:

- thống nhất giữa code, báo cáo, slide và phần demo;
- tránh tuyên bố vượt quá bằng chứng hiện có;
- phân biệt prototype phục vụ đồ án tốt nghiệp với hệ thống production;
- xác định các tiêu chí cần chứng minh trước khi bảo vệ;
- làm cơ sở cho roadmap production sau đồ án.

## 2. Tuyên bố chính thức

LearnMate là một prototype/MVP hỗ trợ việc học tiếng Anh cho người học Việt Nam. Hệ thống cung cấp nội dung học, bài tập, tiến trình, lớp học và phản hồi mang tính formative do AI hỗ trợ.

LearnMate không phải là:

- hệ thống thi IELTS hoặc hệ thống cấp chứng chỉ;
- công cụ đánh giá năng lực ngôn ngữ chính thức;
- công cụ đánh giá phát âm chuyên nghiệp;
- nền tảng đã được chứng minh phục vụ 100.000 người dùng;
- hệ thống production-ready có đầy đủ backup, monitoring, disaster recovery và autoscaling.

Phản hồi và điểm số từ AI chỉ có mục đích hỗ trợ học tập. Người dùng phải được thông báo rằng kết quả AI có thể không chính xác.

## 3. Người dùng và phạm vi chức năng

### Learner

Trong phạm vi prototype, learner có thể:

- đăng ký và đăng nhập;
- thực hiện onboarding;
- chọn self-study hoặc tham gia class;
- làm placement test;
- nhận learning path bảy ngày;
- học lesson và xem media;
- gửi bài reading, writing hoặc speaking transcript;
- nhận feedback AI có cấu trúc;
- xem lịch sử và tiến trình;
- nộp assignment của class;
- xem feedback của teacher.

### Teacher

Trong phạm vi prototype, teacher có thể:

- đăng ký yêu cầu trở thành teacher;
- được admin duyệt;
- tạo class;
- chia sẻ invite code;
- tạo assignment;
- xem member và submission;
- lưu feedback cho learner.

Mobile teacher mode chỉ là màn hình tổng quan và handoff sang web dashboard. Full teacher dashboard không được triển khai riêng bằng native Flutter.

### Administrator

Trong phạm vi prototype, administrator có thể:

- quản lý user;
- duyệt teacher application;
- quản lý content/media;
- xem một số thống kê;
- thực hiện moderation;
- xem application audit records.

Các audit record hiện là append-only ở tầng ứng dụng, không được tuyên bố là immutable audit log ở cấp database hoặc WORM storage.

## 4. Các luồng phải demo được

### Luồng learner

1. Đăng ký hoặc đăng nhập.
2. Chọn self-study hoặc join class.
3. Hoàn thành onboarding.
4. Làm placement test.
5. Tạo learning path.
6. Mở lesson.
7. Gửi ít nhất một bài reading hoặc writing.
8. Nhận và xem feedback AI.
9. Xem lại lịch sử.

### Luồng teacher

1. Gửi teacher application.
2. Admin duyệt application.
3. Teacher đăng nhập portal.
4. Tạo class.
5. Tạo assignment.
6. Learner join class và submit.
7. Teacher xem submission và lưu feedback.

### Luồng administrator

1. Admin đăng nhập.
2. Xem thống kê hoặc danh sách user.
3. Duyệt teacher application.
4. Thực hiện một thao tác moderation.
5. Kiểm tra audit record tương ứng.

## 5. Ngoài phạm vi của prototype

Các nội dung sau không được trình bày như tính năng đã hoàn thiện:

- password reset;
- email verification;
- MFA;
- refresh-token rotation và session revocation đầy đủ;
- offline-first synchronization;
- notification production;
- pronunciation scoring bằng phoneme/acoustic model;
- official IELTS scoring;
- thanh toán hoặc subscription;
- course publishing/versioning đầy đủ;
- media transcoding production;
- object storage và CDN;
- background worker cho AI;
- autoscaling;
- multi-region deployment;
- disaster recovery;
- backup restore drill;
- production-grade observability;
- load capacity ở mức 100.000 người dùng.

## 6. Môi trường được hỗ trợ

### Development

Development có thể dùng:

- SQLite;
- Mock AI;
- local media directory;
- HTTP localhost/LAN;
- development authentication nếu chỉ chạy local.

Các giá trị này chỉ được phép dùng cho môi trường development.

### Demonstration

Bản demo cần:

- sử dụng dữ liệu mẫu không nhạy cảm;
- sử dụng Mock AI hoặc Gemini với API key được cấp riêng;
- không dùng dữ liệu cá nhân thật nếu chưa có sự đồng ý;
- có thể dựng lại bằng hướng dẫn trong README;
- giới hạn số người dùng và mục đích sử dụng.

### Production

Production hiện chưa được xác nhận. Trước khi triển khai công khai phải có tối thiểu:

- PostgreSQL;
- HTTPS;
- auto schema creation bị tắt;
- migration job riêng;
- AI provider thật được cấu hình;
- rate limit;
- object storage;
- backup và restore;
- logging, monitoring và alerting;
- kiểm thử bảo mật và tải.

## 7. Các giới hạn đã biết

| Giới hạn | Đồ án tốt nghiệp | Production | Hướng xử lý |
|---|---|---|---|
| AI chạy trong request đồng bộ | Cần cải thiện | Không chấp nhận | Chuyển sang job queue/worker. |
| Mock AI được dùng cho test | Chấp nhận được nếu ghi rõ | Không chấp nhận | Thêm real-provider contract test và quality evaluation. |
| Local media storage | Chấp nhận được cho demo | Không chấp nhận | Dùng object storage và CDN. |
| SQLite development default | Chấp nhận được cho local | Không chấp nhận | Bắt buộc PostgreSQL ở production. |
| Chưa có rate limiting | Cần cải thiện | Không chấp nhận | API gateway hoặc Redis-backed limiter. |
| Chưa có password reset/email verification | Cần cải thiện | Cần cải thiện | Bổ sung trước public registration. |
| Chưa có MFA cho admin | Có thể nằm ngoài phạm vi | Không chấp nhận | Thêm step-up/MFA cho thao tác nhạy cảm. |
| Chưa có backup/restore | Có thể nằm ngoài phạm vi | Không chấp nhận | Thiết lập backup tự động và restore drill. |
| Chưa có load test | Cần cải thiện | Không chấp nhận | Đo p95/p99, throughput và giới hạn concurrency. |
| Chưa có đánh giá AI với con người | Không chấp nhận nếu AI là đóng góp chính | Không chấp nhận | Xây bộ dữ liệu và rubric đánh giá. |
| Study reminder chưa có notification thật | Không chấp nhận nếu trình bày là hoàn chỉnh | Không chấp nhận | Hoàn thiện hoặc loại khỏi phạm vi demo. |

## 8. Tiêu chí đánh giá AI

Bộ đánh giá tối thiểu nên có 30–50 mẫu, gồm các loại input khác nhau:

- bài đúng và bài có lỗi;
- nhiều trình độ;
- input ngắn và dài;
- input ngoài chủ đề;
- input có lỗi chính tả;
- input không phù hợp;
- input bằng tiếng Việt;
- input rỗng hoặc vượt giới hạn.

Mỗi kết quả nên được đánh giá theo thang điểm hoặc nhãn thống nhất:

1. Phát hiện lỗi có đúng không.
2. Feedback có hữu ích không.
3. Feedback có phù hợp trình độ không.
4. Điểm số có hợp lý không.
5. Có hallucination không.
6. Output có đúng schema không.
7. Thời gian phản hồi và chi phí là bao nhiêu.

Nên có ít nhất một baseline để so sánh, ví dụ:

- rule-based grammar checks;
- feedback viết thủ công;
- hoặc kết quả đánh giá của giáo viên.

Kết quả đánh giá phải được ghi vào báo cáo, không chỉ trình bày bằng lời.

## 9. Tiêu chí kiểm thử trước bảo vệ

### Bắt buộc

- backend tests pass;
- Flutter tests pass;
- admin tests pass;
- kiểm tra quyền của learner, teacher và admin;
- kiểm tra user không truy cập được dữ liệu user khác;
- kiểm tra token hết hạn;
- kiểm tra input không hợp lệ;
- kiểm tra AI response lỗi hoặc thiếu trường;
- kiểm tra duplicate request quan trọng;
- kiểm tra upload file vượt giới hạn;
- kiểm tra migration trên database sạch.

### Nên bổ sung

- PostgreSQL integration test;
- browser E2E cho admin;
- test trên thiết bị Android thật;
- test mất mạng;
- test camera, microphone, STT và video;
- concurrency test cho self-space, vocabulary và class join;
- test migration với dữ liệu cũ;
- load test cơ bản.

## 10. Các tuyên bố được phép và không được phép

### Được phép tuyên bố

- Hệ thống là prototype/MVP.
- Hệ thống hỗ trợ formative learning.
- AI có output có cấu trúc và được kiểm tra schema.
- Hệ thống có các luồng learner, teacher và admin trong phạm vi demo.
- Hệ thống có test tự động cho các luồng chính.
- SQLite được dùng cho development.
- Media local được dùng cho prototype.
- Pronunciation assessment chưa được triển khai.

### Không được tuyên bố nếu chưa có bằng chứng

- Hệ thống production-ready.
- Hệ thống chịu được 100.000 người dùng.
- AI feedback chính xác như giáo viên.
- Điểm AI tương đương điểm IELTS.
- Hệ thống có audit log immutable.
- Hệ thống đã bảo mật đầy đủ.
- Hệ thống có disaster recovery.
- Hệ thống có high availability.
- Hệ thống có pronunciation scoring.

## 11. Tiêu chí nghiệm thu học thuật

Đồ án nên được xem là đủ điều kiện bảo vệ khi:

- phạm vi được ghi rõ;
- các luồng chính demo ổn định;
- không có placeholder được giới thiệu như tính năng hoàn chỉnh;
- phân quyền cơ bản hoạt động đúng;
- có test và kết quả cụ thể;
- có đánh giá AI trên bộ dữ liệu mẫu;
- có sơ đồ kiến trúc, ERD và sequence diagram;
- có bảng giới hạn;
- có hướng dẫn dựng lại hệ thống;
- sinh viên giải thích được các lựa chọn kỹ thuật;
- sinh viên thừa nhận rõ những gì chưa làm.

## 12. Roadmap sau khi bảo vệ

### Giai đoạn production 1: Correctness

- partial unique index cho self-space;
- normalized vocabulary key;
- database check constraints;
- pagination và index;
- idempotency key;
- validate AI output trước commit;
- xử lý session hết hạn.

### Giai đoạn production 2: Reliability

- AI job table;
- worker queue;
- retry/circuit breaker;
- provider quota và cost tracking;
- object storage;
- media validation;
- cleanup job.

### Giai đoạn production 3: Security

- rate limiting;
- refresh-token rotation;
- revoke session;
- password reset;
- email verification;
- MFA admin;
- HTTPS;
- CSP/HSTS;
- audit retention.

### Giai đoạn production 4: Operations

- PostgreSQL integration;
- monitoring;
- structured logging;
- error tracking;
- alerting;
- backup;
- restore drill;
- immutable deployment;
- rollback;
- load test.

## 13. Trách nhiệm của báo cáo

Báo cáo phải phân biệt rõ:

- chức năng đã triển khai;
- chức năng đã kiểm thử;
- chức năng chỉ là kế hoạch;
- giới hạn của prototype;
- rủi ro khi chuyển sang production;
- các phần phụ thuộc vào Gemini hoặc dịch vụ bên ngoài.

Không nên dùng từ “hoàn chỉnh”, “an toàn”, “scalable” hoặc “production-ready” nếu chưa có bằng chứng tương ứng.

