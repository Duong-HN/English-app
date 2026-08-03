# Architecture

## Product boundary

LearnMate AI gives formative feedback for Vietnamese English learners. It is not an accredited language examination. Speaking is intentionally split into:

1. STT transcript evaluation: relevance, grammar and vocabulary.
2. Future pronunciation assessment: short target-word audio compared at phoneme level.

STT text is never presented as evidence of pronunciation accuracy.

## Scope and deployment status

This architecture describes a graduation-project prototype/MVP. It is designed to demonstrate the learner, teacher and administrator workflows on a small controlled dataset and is not a claim of production readiness or 100,000-user capacity.

Development and demonstration may use SQLite, Mock AI, local media storage and HTTP localhost/LAN URLs. A public deployment must not use those defaults without an explicit security review and additional infrastructure. Production work remains separate: PostgreSQL validation, asynchronous AI jobs, object storage, rate limiting, observability, backups, recovery testing and rollout/rollback controls.

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Mobile | Flutter 3.41 / Dart 3.11 | Auth, camera, OCR, microphone, learning UI |
| Teacher/admin web | React 19 / Next-compatible vinext | Teacher classes plus operations and moderation |
| OCR | ML Kit Text Recognition | Latin text extraction on Android/iOS |
| STT | Device speech recognition | English transcript capture |
| API | FastAPI / Python 3.14 | Auth, onboarding, classes, validation, AI orchestration and history |
| ORM/migrations | SQLAlchemy / Alembic | Relational persistence and versioned schema |
| Database | SQLite dev, PostgreSQL prod | Users, analyses, learning paths and audit records |
| Media storage | Private mounted volume (`MEDIA_STORAGE_DIR`) | Audio/video binaries outside the relational database |
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

Lesson media and AI grounding flow:

```text
Admin -> API: multipart audio/video + transcript/caption
API -> Private media volume: store binary with generated key
API -> Database: LessonMedia metadata and lesson relationship
Learner -> API: lesson + authenticated media stream URL
Flutter -> Audio/Video player: stream with Bearer token
Flutter -> API: media position/completion
Learner -> API: OCR/text answer + lesson_id
API -> AI provider: learner input + lesson objective/body/transcript context
API -> Database: analysis with lesson_id and space boundary
```

Learning-path flow:

```text
Learner -> Flutter: goal + CEFR level + minutes per day
Flutter -> API: authenticated generation request
API -> Database: summarize up to 20 recent analyses
API -> Mock/Gemini: summary + fixed seven-day JSON schema
API -> Database: validate and persist learner-owned path
API -> Flutter: focus areas, seven tasks and measurable checkpoints
```

Onboarding, space switching and class-work flow:

```text
Learner -> API: choose self-study or submit a class invite code
Learner -> API: X-Learning-Space-ID when switching spaces
API -> Database: self space or one isolated class space per membership
Learner -> API: goal code + daily minute budget (self space only)
Learner -> API: all 20 placement answers
API -> Database: placement result + skill scores
Learner -> API: complete onboarding
API -> AI/Database: validate and persist one seven-day path in self space
Teacher -> API: class + assignment + deadline
Learner or approved teacher -> API: assignment submission in the class space
API -> assignment grading queue: validate, persist submission state and enqueue idempotent job
Worker -> AI/Database: structured analysis and submission completion
Teacher -> API: review submission and save feedback
API -> Learner or approved teacher: home for the selected space only
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

Teacher and administrator web access share one portal but use role-based entry points:

```text
Teacher -> Mobile Settings: switch to teacher mode
Mobile -> Teacher mode: show overview and web-dashboard handoff
Teacher -> Web: sign in with the same account
Web -> API: login and server-validated teacher role
Teacher -> Web: create class, assign work, review submissions and save feedback

Admin -> Web: sign in with the administrator account
Web -> API: login and server-validated admin role
Admin -> Web: manage users, teacher applications, content, moderation and audit data
```

Learner accounts are intentionally limited to the mobile learning experience. A teacher account can still switch back
to learner mode on mobile and use the same account to study or complete learner-facing class work. The mobile teacher
screen is not a second native implementation of the full web dashboard.

## Database

### users

`id`, `email`, `password_hash`, `display_name`, `role`, `level`, `is_active`, `created_at`, `updated_at`, `last_login_at`

### analyses

`id`, `user_id`, `space_id`, `type`, `input_text`, `result`, `score`, `provider`, `lesson_id`, `created_at`

`analyses.user_id` and `analyses.space_id` are cascading foreign keys. Prototype analysis queries include the authenticated
user and active space. AI-specific output remains JSON for MVP flexibility and every provider path is required to validate
the response before persistence; this invariant must be covered by tests before production.

### learning spaces and curriculum

`learning_spaces` is intended to contain one self-study row per user and one class row per joined class. The self-study
uniqueness invariant requires a database partial unique index and concurrency testing before production. `learning_paths`,
`placement_attempts`, `analyses`, `vocabulary_items` and `lesson_progress` carry `space_id`; their unique and query
`lessons` hold the fixed catalog; `lesson_progress` attaches it to a self-study space. `lesson_media` stores one or
more published/draft audio/video assets per lesson, while `lesson_progress.media_progress` stores position and
completion per media item. Media binaries are not stored in PostgreSQL/SQLite.

### admin_audit_logs

`id`, `admin_user_id`, `action`, `target_type`, `target_id`, `details`, `created_at`

Administrative authorization is enforced by the API. The dashboard is only a client and cannot grant itself access. Audit entries record state changes and moderation actions while excluding passwords, tokens and full learner submissions.

### learning_paths

`id`, `user_id`, `space_id`, `goal`, `current_level`, `minutes_per_day`, `plan`, `provider`, `created_at`

`learning_paths.user_id` cascades on user deletion. The initial path-creation flow schema-validates the JSON plan and expects seven daily tasks. Every update or adaptation path must enforce the same validation before production. Personalization is derived from aggregate counts, scores and issue titles rather than sending full historical submissions to the provider.

### onboarding and placement

`learner_profiles` stores one row per learner with a goal code, daily-minute budget and completion timestamp.
`placement_attempts` stores submitted answers, total score, level, per-skill scores and test version. Public question
responses never include answer keys. Onboarding status is computed from persisted prerequisites, so a learner can
resume on another device. A legacy learner with an existing path is backfilled as completed.

### teacher classes

`classes` belongs to exactly one teacher and has a unique invite code. `class_members` is unique by class and learner.
`assignments` belongs to a class and validates its skill, estimated duration and deadline. `assignment_submissions` is
unique by assignment and learner and points to the persisted `analyses` result. `assignment_grading_jobs` stores the
queue state, retry metadata and idempotency fingerprint; the worker changes a submission from `processing` to
`submitted` only after a successful provider call. A resubmission updates the existing records. Teacher ownership is
enforced on member lists, submission review and feedback; learners can only see classes
they joined. Administrator access is explicit and does not turn teachers into administrators.

## Security boundaries

- Passwords use Argon2 through `pwdlib`.
- JWTs expire and contain only the user ID.
- Tokens are stored with Flutter secure storage.
- Admin JWTs are tab-scoped in browser `sessionStorage`, not persistent local storage. This is a prototype trade-off, not the recommended production session architecture.
- Gemini keys remain server-side and are ignored by Git.
- Development identity headers are disabled in production.
- Administrator endpoints require an active server-validated `admin` role.
- The final active administrator and the current administrator session are protected from accidental lockout.
- Production settings reject weak JWT secrets.
- Lesson media uploads validate declared media type, size and private storage paths; stream access requires authentication. Magic-byte validation, malware scanning, entitlement checks and object storage remain production work.
- Release signing keys are GitHub secrets, never repository files.

## Known production boundaries

- Add rate limiting through an API gateway or Redis-backed limiter before public launch.
- Add password reset/email verification before public registration.
- Add observability and personal-data retention rules.
- Validate pronunciation with a dedicated acoustic/phoneme pipeline, not an LLM transcript score.
- Move AI analysis and assignment processing to an idempotent background job before public scale.
- Replace local media volumes with object storage and CDN delivery before horizontal scaling.
- Add PostgreSQL integration, migration rollout/rollback testing, backups and restore drills.
- Add human-reviewed AI quality evaluation; schema-valid JSON alone does not prove educational correctness.
