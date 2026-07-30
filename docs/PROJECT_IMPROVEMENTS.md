# Các điểm cần cải thiện của đồ án LearnMate

## 1. Kết luận tổng quát

Đồ án hiện phù hợp với phạm vi **prototype/MVP cho đồ án tốt nghiệp**. Đồ án chưa đủ cơ sở để tuyên bố là hệ thống production-ready hoặc có thể phục vụ quy mô lớn.

Đánh giá tham khảo:

- Đồ án tốt nghiệp: **6.5–7/10**, có thể đạt nếu bổ sung đánh giá, tài liệu và sửa các lỗi quan trọng.
- Hệ thống production: **chưa đạt**.

Không nên tuyên bố hệ thống có thể phục vụ 100.000 người dùng nếu chưa có benchmark, load test, monitoring, backup, queue AI và object storage.

## 2. Quy ước đánh giá

- **Đồ án tốt nghiệp — Chấp nhận được:** phù hợp với prototype nếu được giới hạn và giải thích rõ.
- **Đồ án tốt nghiệp — Cần cải thiện:** chưa đủ tốt về học thuật hoặc kỹ thuật nhưng có thể sửa.
- **Đồ án tốt nghiệp — Không chấp nhận:** ảnh hưởng trực tiếp đến tính đúng đắn hoặc tuyên bố chính của đồ án.
- **Production — Chấp nhận được:** không tạo blocker nghiêm trọng.
- **Production — Cần cải thiện:** có thể chạy giới hạn nhưng chưa nên mở rộng.
- **Production — Không chấp nhận:** phải sửa trước khi triển khai công khai.

## 3. Việc bắt buộc hoàn thành trước khi bảo vệ

### 3.1. Làm rõ phạm vi và tuyên bố

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận nếu vẫn tuyên bố production-ready.

Thêm rõ trong báo cáo và slide:

- Đây là prototype/MVP.
- Quy mô kiểm thử hiện tại là quy mô nhỏ.
- AI được dùng để hỗ trợ học tập, không phải công cụ đánh giá năng lực chính thức.
- Chưa triển khai object storage, queue AI, autoscaling, backup và disaster recovery.
- Các giới hạn của hệ thống là giới hạn đã biết, không phải tính năng đã hoàn thiện.

### 3.2. Bổ sung đánh giá chất lượng AI

Ảnh hưởng đến:

- [backend/app/ai.py](../backend/app/ai.py)
- [backend/app/routers/analyses.py](../backend/app/routers/analyses.py)
- [backend/app/routers/learning_paths.py](../backend/app/routers/learning_paths.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện; Không chấp nhận nếu AI là đóng góp chính nhưng không được đánh giá.
- Production: Không chấp nhận.

Cần bổ sung:

1. Bộ dữ liệu mẫu có nhiều mức độ và loại lỗi.
2. Tiêu chí đánh giá feedback AI.
3. Đánh giá bởi ít nhất một người có chuyên môn tiếng Anh hoặc giáo viên.
4. So sánh với baseline đơn giản, ví dụ rule-based hoặc feedback thủ công.
5. Đo độ chính xác, độ nhất quán và tỷ lệ hallucination.
6. Ghi nhận các trường hợp AI trả kết quả sai hoặc không đủ thông tin.
7. Nhãn rõ ràng rằng feedback là AI-generated và có thể sai.

Không nên chỉ dùng tiêu chí “API trả JSON đúng schema” để kết luận AI hoạt động tốt.

### 3.3. Bổ sung test và bằng chứng

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận nếu thiếu các test quan trọng.

Cần bổ sung hoặc ghi rõ kết quả của:

- Test với PostgreSQL thật.
- Test quyền truy cập của learner, teacher và admin.
- Test token hết hạn và đăng nhập sai nhiều lần.
- Test AI timeout, provider lỗi và response không hợp lệ.
- Test upload file sai MIME type, file quá lớn và file giả mạo extension.
- Test gửi request trùng lặp.
- Test hai request đồng thời tạo learning space.
- Test hai request đồng thời join class.
- Test migration trên database đã có dữ liệu.
- Test browser cho các flow admin quan trọng.
- Test thiết bị thật cho camera, microphone, speech-to-text và video.

Các test hiện có vẫn có giá trị, nhưng cần giải thích rõ rằng test hiện tại chưa bao phủ production behavior.

### 3.4. Tính năng chưa hoàn chỉnh

| Tính năng | Đồ án tốt nghiệp | Production | Cần làm |
|---|---|---|---|
| Study reminder chỉ thay đổi trạng thái local | Không chấp nhận nếu giới thiệu là hoàn chỉnh | Không chấp nhận | Hoặc triển khai notification thật, hoặc ghi rõ là placeholder và ẩn khỏi bản demo chính. |
| AI analysis chạy đồng bộ | Cần cải thiện | Không chấp nhận | Bổ sung trạng thái pending/failed và xử lý nền. |
| Media lưu local | Chấp nhận được cho demo | Không chấp nhận | Chuyển sang object storage nếu triển khai thật. |
| SQLite là default | Chấp nhận được cho local | Không chấp nhận | Production phải bắt buộc PostgreSQL. |
| Mock AI | Chấp nhận được cho test/demo | Không chấp nhận | Production phải fail nếu provider chưa được cấu hình. |

## 4. Các lỗi kỹ thuật cần sửa

### 4.1. Cấu hình production không được fail-open

Files:

- [backend/app/config.py](../backend/app/config.py)
- [docker-compose.yml](../docker-compose.yml)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Production phải từ chối khởi động nếu:

- database không phải PostgreSQL;
- auto_create_schema đang bật;
- AI provider vẫn là mock;
- JWT secret là giá trị mặc định;
- origin dùng HTTP hoặc localhost;
- thiếu API key của AI provider;
- media storage chưa được cấu hình an toàn.

### 4.2. Sửa race condition của self-learning space

Files:

- [backend/app/models.py](../backend/app/models.py)
- [backend/app/learning_spaces.py](../backend/app/learning_spaces.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Cần:

1. Chuẩn hóa điều kiện kind và class_id.
2. Thêm partial unique index cho một self-space trên mỗi user.
3. Xử lý lỗi duplicate do request đồng thời.
4. Viết test concurrency.

Ví dụ thiết kế database:

    CREATE UNIQUE INDEX uq_one_self_space_per_user
    ON learning_spaces(user_id)
    WHERE kind = 'self' AND class_id IS NULL;

### 4.3. Chuẩn hóa vocabulary ở database

Files:

- [backend/app/models.py](../backend/app/models.py)
- [backend/app/routers/vocabulary.py](../backend/app/routers/vocabulary.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Không nên chỉ kiểm tra lower(word) trong Python. Nên lưu thêm word_normalized và tạo unique constraint trên giá trị đã chuẩn hóa.

### 4.4. Không giữ database session trong lúc chờ AI

Files:

- [backend/app/ai.py](../backend/app/ai.py)
- [backend/app/routers/analyses.py](../backend/app/routers/analyses.py)
- [backend/app/routers/classes.py](../backend/app/routers/classes.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Luồng nên là:

    API nhận request
      -> lưu analysis_job với trạng thái queued
      -> trả 202 Accepted
      -> worker gọi AI
      -> worker lưu kết quả
      -> client đọc trạng thái job

Không nên giữ request và database connection trong suốt thời gian Gemini xử lý.

### 4.5. Validate AI output trước khi commit

File:

- [backend/app/routers/learning_paths.py](../backend/app/routers/learning_paths.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Mọi output từ AI phải được validate bằng schema trước khi lưu database. Không lưu raw response chỉ vì provider trả về JSON.

### 4.6. Thêm pagination và index

Các khu vực cần rà soát:

- class list;
- assignment list;
- submission list;
- member list;
- admin user search;
- analysis history;
- learning-path history;
- home dashboard.

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận ở quy mô lớn.

Mỗi collection nên có limit mặc định, max limit, thứ tự ổn định bằng created_at và id, cursor pagination cho dữ liệu lớn, cùng index phù hợp.

### 4.7. Sửa upload media

Files:

- [backend/app/media_storage.py](../backend/app/media_storage.py)
- [backend/app/routers/content.py](../backend/app/routers/content.py)

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Cần bổ sung:

- kiểm tra magic bytes;
- giới hạn request body trước multipart parsing;
- kiểm tra duration, codec và kích thước media;
- virus scanning nếu nhận file từ người dùng;
- cleanup file mồ côi;
- HTTPS cho external media URL;
- kiểm tra quyền truy cập trước khi stream.

## 5. Cải thiện kiến trúc mã nguồn

### Backend

Nên tách dần router thành:

    api/routes/
    application/services/
    domain/policies/
    infrastructure/repositories/
    infrastructure/ai/
    infrastructure/media/

Ưu tiên tách các nghiệp vụ:

1. AI analysis.
2. Assignment submission.
3. Learning-path generation.
4. Class membership.
5. Media lifecycle.
6. Admin role và teacher approval.

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Cần cải thiện mạnh.

### Flutter

Các file như [home_page.dart](../mobile/lib/src/pages/home_page.dart) và [curriculum_page.dart](../mobile/lib/src/pages/curriculum_page.dart) nên tách thành:

- typed models;
- repositories;
- controllers/view models;
- reusable widgets;
- error/loading states.

Mức độ:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Cần cải thiện.

Không cần rewrite toàn bộ. Chỉ cần chứng minh rõ kiến trúc và tách các phần có rủi ro cao.

### Admin dashboard

File [admin-app.tsx](../admin-dashboard/src/admin-app.tsx) nên được tách theo module:

- users;
- teacher applications;
- classes;
- media;
- audit logs;
- dashboard statistics.

## 6. Bảo mật tối thiểu cần bổ sung

| Hạng mục | Đồ án tốt nghiệp | Production |
|---|---|---|
| Login rate limit | Cần cải thiện | Không chấp nhận nếu thiếu |
| Refresh token và revoke session | Cần cải thiện | Không chấp nhận |
| MFA cho admin | Có thể nằm ngoài phạm vi | Không chấp nhận với admin công khai |
| HTTPS bắt buộc | Cần cải thiện | Không chấp nhận nếu thiếu |
| Upload validation | Cần cải thiện | Không chấp nhận nếu thiếu |
| Media authorization | Cần cải thiện | Không chấp nhận nếu thiếu |
| AI privacy/consent | Cần cải thiện | Không chấp nhận nếu thiếu |
| Security headers | Cần cải thiện | Cần cải thiện |
| Audit log đầy đủ | Cần cải thiện | Cần cải thiện |

Trong báo cáo nên có mục Security limitations thay vì im lặng bỏ qua.

## 7. DevOps và triển khai

Mức độ hiện tại:

- Đồ án tốt nghiệp: Cần cải thiện.
- Production: Không chấp nhận.

Cần bổ sung hoặc mô tả rõ:

- PostgreSQL production;
- migration job riêng;
- secret management;
- backup và restore;
- logging;
- health check;
- monitoring;
- alerting;
- rollback;
- image immutable tag/digest;
- kiểm thử Docker image trong CI;
- kiểm thử release APK thật.

Không cần triển khai Kubernetes cho đồ án. Nhưng cần chứng minh quy trình chạy hệ thống bằng Docker Compose hoặc một môi trường cụ thể là ổn định và tái lập được.

## 8. Tài liệu cần bổ sung vào báo cáo

1. Sơ đồ kiến trúc tổng thể.
2. Sơ đồ sequence cho AI analysis.
3. Sơ đồ sequence cho assignment submission.
4. ERD và giải thích các quan hệ quan trọng.
5. Ma trận quyền learner/teacher/admin.
6. Bảng ánh xạ yêu cầu đến chức năng đến test case.
7. Bảng các giới hạn của hệ thống.
8. Phương pháp đánh giá AI.
9. Kết quả kiểm thử thực tế.
10. Môi trường chạy và hướng dẫn tái hiện.
11. Threat model cơ bản.
12. Chính sách xử lý dữ liệu gửi cho AI.

## 9. Tiêu chí nghiệm thu đề xuất

Đồ án có thể xem là đạt yêu cầu bảo vệ nếu đáp ứng tối thiểu:

- Demo được các luồng chính learner, teacher và admin.
- Không có lỗi nghiêm trọng trong luồng đăng nhập và phân quyền.
- Không để các tính năng placeholder xuất hiện như tính năng hoàn chỉnh.
- Có test cho các chức năng chính và lỗi phổ biến.
- Có đánh giá AI bằng dữ liệu mẫu và tiêu chí rõ ràng.
- Có báo cáo giới hạn của SQLite, mock AI, local media và synchronous AI.
- Có sơ đồ kiến trúc và giải thích lựa chọn công nghệ.
- Có thể dựng lại hệ thống từ tài liệu hướng dẫn.
- Không tuyên bố quá mức về scalability hoặc production readiness.

## 10. Lộ trình ưu tiên

### Ưu tiên 1 — Bắt buộc trước bảo vệ

- Làm rõ phạm vi prototype.
- Bổ sung đánh giá chất lượng AI.
- Bổ sung ma trận yêu cầu và test case.
- Viết threat model và security limitations.
- Sửa hoặc ẩn Study reminder chưa hoạt động.
- Sửa các lỗi cấu hình production nguy hiểm.
- Bổ sung test phân quyền và lỗi AI.
- Bổ sung sơ đồ kiến trúc, ERD và sequence diagram.

### Ưu tiên 2 — Cần làm nếu muốn demo đáng tin cậy hơn

- Sửa race condition self-space.
- Chuẩn hóa vocabulary uniqueness.
- Thêm pagination và index chính.
- Validate AI output trước khi commit.
- Xử lý session hết hạn trên mobile/admin.
- Bổ sung timeout và retry có kiểm soát.
- Kiểm thử PostgreSQL thật.

### Ưu tiên 3 — Cần làm nếu triển khai production

- Đưa AI sang worker queue.
- Chuyển media sang object storage.
- Thêm rate limit, refresh token, revoke session và MFA admin.
- Bổ sung upload security đầy đủ.
- Thêm monitoring, logging, backup và rollback.
- Thêm load test và E2E test.
- Chuẩn hóa deployment pipeline.

## 11. Kết luận dành cho hội đồng

Đồ án có khối lượng triển khai tốt và có thể được chấp nhận như một prototype học tập có AI. Tuy nhiên, đồ án cần giảm các tuyên bố về production, bổ sung đánh giá AI, kiểm thử có bằng chứng và trình bày trung thực các giới hạn.

Phân biệt rõ:

- **Đối với đồ án tốt nghiệp:** chưa cần đạt chuẩn nền tảng thương mại lớn, nhưng phải chứng minh được tính đúng đắn, hiểu kiến trúc và biết giới hạn.
- **Đối với production:** hệ thống hiện chưa đạt vì còn thiếu các thành phần về bảo mật, concurrency, vận hành, dữ liệu, AI reliability và scalability.

