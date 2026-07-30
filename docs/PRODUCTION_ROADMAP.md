# Roadmap triển khai production LearnMate

## 1. Trạng thái hiện tại

LearnMate hiện là prototype/MVP phục vụ đồ án tốt nghiệp.

Không được coi việc CI pass, Docker image build hoặc API chạy được là bằng chứng production-ready. Trước public launch cần hoàn thành các gate trong tài liệu này.

Mục tiêu 100.000 daily users là mục tiêu capacity planning tương lai, không phải tuyên bố hiện tại.

## 2. Kiến trúc đích được đề xuất

Không cần chuyển ngay sang microservices. Kiến trúc phù hợp nhất là modular monolith có các worker riêng cho tác vụ chậm:

    Flutter mobile
          |
    Teacher/Admin web
          |
    HTTPS reverse proxy / API gateway
          |
    FastAPI API replicas
       |       |        |
       |       |        +-- Object storage/CDN
       |       +----------- Redis rate limit/cache
       +------------------- PostgreSQL
          |
       AI job queue
          |
       AI worker replicas

### Thành phần

| Thành phần | Vai trò | Trạng thái cần đạt |
|---|---|---|
| FastAPI API | Auth, CRUD, validation, authorization | Chạy stateless và scale ngang |
| PostgreSQL | Dữ liệu giao dịch | Managed service, backup, tested restore |
| Redis hoặc tương đương | Rate limit, cache, job coordination | Không dùng làm source of truth |
| Queue/worker | AI analysis, assignment processing, media jobs | Retry, idempotency, dead-letter handling |
| Object storage | Audio, video, captions | Private bucket, signed access, lifecycle |
| CDN | Phân phối media | Cache an toàn, origin protection |
| Observability | Log, metric, trace, alert | Có request ID và AI cost metrics |
| API gateway | TLS, rate limit, body limits | Fail closed trước API |

## 3. Nguyên tắc triển khai

1. Không mở public trước khi hoàn thành security gate.
2. Không giữ database session trong lúc chờ AI hoặc file processing.
3. Không dùng local filesystem làm storage khi có nhiều API replica.
4. Không chạy migration trong mọi API container.
5. Không dùng mutable latest làm định danh duy nhất để rollback.
6. Không coi JSON schema là bằng chứng AI đúng.
7. Không đưa dữ liệu cá nhân thật vào AI khi chưa có consent và retention policy.
8. Không thêm microservices nếu modular monolith chưa có số liệu chứng minh cần tách.
9. Mọi mutation có thể retry phải có idempotency strategy.
10. Mọi release phải có health verification và rollback plan.

## 4. Giai đoạn 0 — Chốt phạm vi và thiết kế

### Mục tiêu

Tạo baseline được hội đồng và team chấp nhận trước khi đầu tư production.

### Việc cần làm

- Chốt prototype scope.
- Ghi rõ non-goals.
- Chốt data classification cho learner text, media và AI result.
- Viết threat model.
- Viết architecture decision records cho:
  - AI synchronous hiện tại;
  - worker queue tương lai;
  - PostgreSQL;
  - object storage;
  - JWT/session;
  - deployment platform.
- Xác định expected peak traffic từ telemetry sau beta.

### Exit criteria

- Không còn tài liệu nào gọi prototype là production-ready.
- Có sơ đồ trust boundary.
- Có danh sách tài sản cần bảo vệ.
- Có owner cho từng production control.
- Có backlog production được ưu tiên.

## 5. Giai đoạn 1 — Correctness và database

### Việc cần làm

- Bắt buộc PostgreSQL ở production.
- Thêm partial unique index cho một self-space trên mỗi user.
- Chuẩn hóa vocabulary key.
- Thêm check constraints cho role, status, skill, score và progress.
- Thêm composite indexes theo query plan.
- Thêm cursor pagination cho collection lớn.
- Thêm tie-breaker id vào mọi pagination order.
- Tạo idempotency key cho:
  - AI analysis;
  - assignment submission;
  - learning-path generation;
  - media upload.
- Tách attempt history nếu assignment resubmission cần audit đầy đủ.
- Thực hiện migration theo expand/contract.
- Kiểm thử migration với dữ liệu đại diện và dữ liệu lỗi.

### Exit criteria

- PostgreSQL integration suite pass.
- Concurrency tests pass.
- Migration upgrade và rollback plan được rehearsal.
- Không có duplicate self-space trong dữ liệu hiện hữu.
- Không có collection API không giới hạn.
- Query plans được lưu cho các endpoint chính.

## 6. Giai đoạn 2 — AI reliability

### API

POST analysis không nên chờ provider hoàn tất. API nên:

1. validate input;
2. tạo AI job;
3. commit job;
4. trả 202 Accepted;
5. client polling hoặc nhận notification;
6. trả kết quả khi worker hoàn tất.

### Worker

Worker phải có:

- job status: queued, running, completed, failed, cancelled;
- attempt count;
- provider/model;
- timeout;
- retry có exponential backoff và jitter;
- idempotency key;
- dead-letter hoặc manual retry;
- prompt version;
- token usage;
- estimated cost;
- error category;
- request correlation ID.

### AI safety

- Không gửi toàn bộ lịch sử nếu không cần.
- Giới hạn prompt và output token.
- Redact dữ liệu nhạy cảm.
- Không cho AI tự quyết định quyền hoặc vai trò.
- Validate output bằng schema trước khi lưu.
- Có fallback khi provider unavailable.
- Gắn nhãn feedback là AI-generated.
- Không tuyên bố điểm chính thức.

### Exit criteria

- Provider timeout không làm cạn database pool.
- Retry không tạo duplicate analysis.
- Có dashboard số job failed, latency và cost.
- Có manual replay cho job failed.
- Có budget per user và per organization.
- Có test provider 200, 400, 429, 500, timeout, empty response và malformed JSON.

## 7. Giai đoạn 3 — Authentication và security

### Authentication

- Access token ngắn hạn.
- Refresh token rotation.
- Session table hoặc revocation mechanism.
- Logout server-side.
- Password reset.
- Email verification.
- Login rate limit.
- Account lockout hoặc progressive delay.
- MFA/step-up cho admin.
- Key rotation procedure.
- JWT issuer và audience validation.

### Web security

- Không lưu admin bearer token như giải pháp production chính.
- Ưu tiên HttpOnly Secure SameSite cookie qua BFF.
- CSP.
- HSTS.
- Permissions-Policy.
- CSRF protection nếu dùng cookie.
- CORS allowlist chính xác.
- Không cho người dùng nhập arbitrary backend origin trong production.
- HTTPS-only external media URL.

### Data security

- Phân loại PII.
- Encryption at rest cho database và object storage.
- Retention/deletion policy.
- User data export/delete.
- AI provider data-processing review.
- Audit retention và restricted access.

### Exit criteria

- Threat model được review.
- Không còn default secret production.
- Dev auth bị vô hiệu hóa ở production.
- Security headers được kiểm tra tự động.
- Upload abuse tests pass.
- Penetration test hoặc security review được ghi nhận.
- Có quy trình xử lý sự cố token bị lộ.

## 8. Giai đoạn 4 — Media platform

### Storage

- Private object-storage bucket.
- Database chỉ lưu metadata và object key.
- Signed URL hoặc authenticated proxy.
- Không trả trực tiếp URL private vĩnh viễn.
- Lifecycle policy cho file orphan và file đã xóa.
- Backup/replication theo yêu cầu.

### Validation

- Magic-byte detection.
- MIME verification.
- File size limit.
- Duration limit.
- Codec/container validation.
- Image dimension limit.
- Malware scan.
- Metadata stripping nếu cần.
- Caption/transcript validation.

### Delivery

- CDN có cache policy rõ.
- ETag và range request.
- Origin protection.
- Entitlement check trước cấp signed URL.

### Exit criteria

- API replicas dùng chung media được.
- Container restart không làm mất file.
- File hỏng không được publish.
- User không truy cập được media ngoài quyền.
- Orphan cleanup có metric và alert.

## 9. Giai đoạn 5 — Observability và vận hành

### Logging

Mọi request cần có:

- request ID;
- user ID đã được redacted phù hợp;
- route;
- status;
- latency;
- response size;
- error code;
- provider/job ID nếu có.

Không log:

- password;
- JWT;
- API key;
- full learner submission;
- raw sensitive prompt;
- raw provider secret.

### Metrics

Theo dõi tối thiểu:

- request rate;
- error rate;
- p50/p95/p99 latency;
- database pool usage;
- queue depth;
- AI latency;
- AI timeout rate;
- AI cost;
- upload failure rate;
- storage usage;
- authentication failures;
- active sessions;
- class join failures.

### Alerts

Cần cảnh báo khi:

- error rate vượt ngưỡng;
- AI timeout tăng;
- queue backlog tăng;
- database pool gần cạn;
- storage gần đầy;
- migration failed;
- backup failed;
- unusual login attempts;
- cost vượt budget.

### Exit criteria

- Có dashboard.
- Có alert route đến người phụ trách.
- Có runbook cho các lỗi phổ biến.
- Có request ID để trace từ client đến provider.
- Có kiểm thử alert ít nhất một lần.

## 10. Giai đoạn 6 — CI/CD và release

### Pipeline

CI phải có:

- lint và format;
- unit test;
- PostgreSQL integration test;
- migration test;
- browser E2E;
- mobile release smoke test;
- dependency audit;
- secret scan;
- SAST;
- container vulnerability scan;
- SBOM;
- Docker build.

### Release

- Dùng immutable image digest.
- Không coi latest là rollback target.
- Migration job chạy trước rollout.
- Rollout theo canary hoặc staged deployment.
- Health check sau deploy.
- Tự động dừng rollout nếu p95/error rate xấu.
- Có rollback ứng dụng.
- Có forward-compatible migration.
- Có release artifact checksum.

### Exit criteria

- Từ một commit có thể tái tạo artifact.
- Có staging smoke test.
- Có rollback rehearsal.
- Deployment failure không để lại trạng thái không biết.
- Production release có approval gate.

## 11. Giai đoạn 7 — Capacity planning

Không chọn con số replica trước khi có dữ liệu. Quy trình:

1. Xác định daily active users.
2. Đo request/user/day.
3. Xác định peak multiplier.
4. Đo tỷ lệ người dùng gọi AI.
5. Xác định provider quota và cost.
6. Tạo workload đại diện.
7. Load test ở mức 1x, 2x và tối thiểu 5x peak dự kiến.
8. Đo p95/p99, error rate, queue depth, database pool và cost.
9. Tìm bottleneck đầu tiên.
10. Tối ưu rồi lặp lại.

### Các ngưỡng nên đặt sau khi có baseline

- CRUD p95;
- AI job completion p95;
- API error rate;
- queue maximum age;
- database pool utilization;
- storage response time;
- cost per active learner.

Không được ghi “hỗ trợ 100.000 users” nếu chưa có workload model và kết quả đo.

## 12. Giai đoạn 8 — Backup và disaster recovery

Cần xác định:

- RPO;
- RTO;
- database backup frequency;
- media backup strategy;
- retention;
- encryption;
- cross-region requirement;
- restore owner;
- incident communication.

Restore drill phải kiểm tra:

1. database có khôi phục được không;
2. media có khôi phục được không;
3. schema version có đúng không;
4. application có khởi động được không;
5. user có truy cập lại dữ liệu đúng không;
6. thời gian khôi phục có đạt RTO không.

## 13. Những việc không làm trước khi có số liệu

- Không tách microservices chỉ vì file router lớn.
- Không dùng Kubernetes nếu chưa có nhu cầu vận hành.
- Không thêm Redis làm source of truth.
- Không tối ưu bundle trước khi đo.
- Không triển khai multi-region trước khi có RPO/RTO.
- Không tăng model hoặc provider AI mà không đo cost/quality.
- Không mở public registration trước khi có abuse controls.

## 14. Production go/no-go checklist

### Không được launch nếu còn một trong các mục sau

- production có thể chạy Mock AI;
- production có thể dùng SQLite;
- production còn bật auto schema creation;
- dev auth có thể bị expose;
- không có rate limit login/AI;
- media private không có entitlement check;
- upload không có body limit;
- không có backup;
- không có monitoring;
- không có rollback;
- migration chạy đồng thời trong nhiều API replica;
- không biết cách revoke token;
- chưa review dữ liệu gửi cho AI;
- chưa có PostgreSQL test.

### Có thể mở beta giới hạn khi

- các luồng chính pass;
- dữ liệu beta không nhạy cảm hoặc đã có consent;
- user count bị giới hạn;
- Mock/Gemini mode được ghi rõ;
- có người trực theo dõi;
- có backup thủ công;
- có cách dừng đăng ký;
- có cách rollback phiên bản.

## 15. Kết quả mong muốn

Roadmap này không biến prototype thành production bằng một lần merge. Nó tạo ra các gate rõ ràng để:

- bảo vệ đồ án trong phạm vi trung thực;
- triển khai beta có kiểm soát;
- đo được bottleneck trước khi scale;
- tránh rewrite không cần thiết;
- nâng cấp từng phần mà không phá vỡ các luồng học tập hiện có.

