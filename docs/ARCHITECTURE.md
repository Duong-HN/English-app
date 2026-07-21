# Architecture

## Product boundary

LearnMate AI gives formative feedback for Vietnamese English learners. It is not an accredited language examination. Speaking is intentionally split into:

1. STT transcript evaluation: relevance, grammar and vocabulary.
2. Future pronunciation assessment: short target-word audio compared at phoneme level.

STT text is never presented as evidence of pronunciation accuracy.

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Mobile | Flutter 3.41 / Dart 3.11 | Auth, camera, OCR, microphone, learning UI |
| Admin web | React 19 / Next-compatible vinext | Operations dashboard, moderation and API Console |
| OCR | ML Kit Text Recognition | Latin text extraction on Android/iOS |
| STT | Device speech recognition | English transcript capture |
| API | FastAPI / Python 3.14 | Auth, validation, AI orchestration, history |
| ORM/migrations | SQLAlchemy / Alembic | Relational persistence and versioned schema |
| Database | SQLite dev, PostgreSQL prod | Users and analyses |
| AI | Mock or Gemini | Structured formative feedback |
| Delivery | Docker / Cloudflare Worker / GitHub Actions / GHCR | Test, package, release and deploy mobile/API/admin |

## Main sequence

```text
Learner -> Flutter: camera image
Flutter -> ML Kit: recognize locally
ML Kit -> Flutter: extracted text
Learner -> Flutter: review/edit text
Flutter -> API: Bearer token + text
API -> AI provider: prompt + JSON schema
AI provider -> API: structured result
API -> Database: persist analysis for user
API -> Flutter: result
```

Administrator flow:

```text
Admin -> Web: email/password
Web -> API: login
API -> Web: JWT + server-validated admin role
Web -> API: Bearer token + administration request
API -> Database: enforce RBAC, mutate/query, append audit record
API -> Web: operational data or structured API Console response
```

## Database

### users

`id`, `email`, `password_hash`, `display_name`, `role`, `level`, `is_active`, `created_at`, `updated_at`, `last_login_at`

### analyses

`id`, `user_id`, `type`, `input_text`, `result`, `score`, `provider`, `created_at`

`analyses.user_id` is a cascading foreign key. Queries always include the authenticated user ID. AI-specific output remains JSON for MVP flexibility but is validated before persistence.

### admin_audit_logs

`id`, `admin_user_id`, `action`, `target_type`, `target_id`, `details`, `created_at`

Administrative authorization is enforced by the API. The dashboard is only a client and cannot grant itself access. Audit entries record state changes and moderation actions while excluding passwords, tokens and full learner submissions.

## Security boundaries

- Passwords use Argon2 through `pwdlib`.
- JWTs expire and contain only the user ID.
- Tokens are stored with Flutter secure storage.
- Admin JWTs are tab-scoped in browser `sessionStorage`, not persistent local storage.
- Gemini keys remain server-side and are ignored by Git.
- Development identity headers are disabled in production.
- Administrator endpoints require an active server-validated `admin` role.
- The final active administrator and the current administrator session are protected from accidental lockout.
- Production settings reject weak JWT secrets.
- Release signing keys are GitHub secrets, never repository files.

## Known production boundaries

- Add rate limiting through an API gateway or Redis-backed limiter before public launch.
- Add password reset/email verification before public registration.
- Add observability and personal-data retention rules.
- Validate pronunciation with a dedicated acoustic/phoneme pipeline, not an LLM transcript score.
