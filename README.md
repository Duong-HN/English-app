# LearnMate AI

LearnMate AI is a graduation-project MVP for formative English learning. It combines a Flutter mobile application, a teacher/administrator web portal, on-device OCR, speech-to-text, a FastAPI backend, PostgreSQL/SQLite and a replaceable AI provider.

> AI feedback and scores are formative. The application does not claim to provide an official IELTS score or infer pronunciation quality from a transcript.

## Scope and limitations

This repository documents and demonstrates a prototype/MVP, not a production-ready or officially accredited assessment system. The supported scope, non-goals, evaluation requirements and known production boundaries are defined in [Scope and limitations](docs/PROJECT_SCOPE_AND_LIMITATIONS.md).

SQLite, Mock AI, local media storage and HTTP localhost/LAN endpoints are development or demonstration options only. Production deployment requires additional work for PostgreSQL, HTTPS, asynchronous AI jobs, object storage, rate limiting, observability, backups and recovery.

## Implemented

- Email/password registration and JWT login.
- Secure token storage on the device.
- Resumable learner onboarding with goal, daily-time preferences and a server-scored 20-question placement test.
- Onboarding choice between self-study and joining a teacher's class; the active space can be changed in Settings.
- API-enforced space-scoped isolation for learner level, placement, path, analysis, vocabulary and lesson progress in the prototype flows.
- Fixed level/chapter curriculum, four IELTS band tracks (4.5–8.0), and a lesson library API with progress tracking.
- Real lesson media pipeline: admin uploads licensed audio/video or registers a hosted URL; mobile plays it with
  authenticated streaming, transcript/caption and resumable media progress.
- Home dashboard scoped to the active space: self-study shows the personal course/path, class mode shows teacher work.
- Teacher role with class invite codes, assignments, AI-assisted submissions and teacher feedback.
- Structured English A2-to-B1 content pack with six original lessons, practice activities, answer keys and provenance metadata.
- Teacher mode on mobile is a compact overview; full class management remains in the responsive Teacher Dashboard web portal.
- Administrator RBAC, account moderation and append-only application audit records.
- Responsive teacher/administrator web portal for classes, live metrics, moderation and an authenticated API Console.
- Reading analysis with translation, vocabulary and questions.
- Writing feedback with issues, score and rewrite.
- Speaking transcript feedback for relevance, grammar and vocabulary.
- Personalized seven-day learning paths generated from each self-study space's recent activity and persisted history.
- Camera/gallery OCR on Android and iOS using on-device ML Kit.
- Device speech-to-text for English transcripts; pronunciation scoring is intentionally not claimed without an audio
  assessment provider.
- Per-user persisted analysis and learning-path history with ownership-safe deletion.
- SQLite development mode and PostgreSQL production support.
- Alembic database migrations.
- Deterministic Mock AI and optional Gemini adapter with structured output validation.
- Backend, administrator web and Flutter automated tests.
- Docker Compose for PostgreSQL, API and admin web; GitHub Actions CI, signed APK release, GHCR images and deployment hooks.

## Architecture

```text
Flutter mobile                         Teacher/admin web
  ├─ secure auth token                        ├─ operations dashboard
  ├─ onboarding + self/class spaces           ├─ classes and assignments
  ├─ camera -> OCR -> editable text           ├─ curriculum media manager
  └─ microphone -> STT transcript              └─ authenticated API Console
                 |                                      |
                 +----------> FastAPI REST API <---------+
                                   |
                         +---------+---------+
                         v                   v
                 PostgreSQL/SQLite    Mock AI or Gemini
```

## Repository layout

```text
backend/           FastAPI, database migrations and backend tests
mobile/            Flutter application for Android, iOS and web preview
admin-dashboard/   Teacher/administrator dashboard and authenticated API Console
postman/           Versioned API collection and secret-free local environment
docs/              Architecture, API, testing and deployment documentation
scripts/           Local verification and release-readiness scripts
docker-compose.yml Shared PostgreSQL, API and dashboard environment
```

Each application owns its source code, dependencies, tests and production
container definition. Only shared automation, documentation and Compose files
remain at the repository root.

## Quick start with local Python

Backend:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Flutter web development preview:

```powershell
cd mobile
flutter pub get
flutter run -d chrome `
  --dart-define=API_BASE_URL=http://localhost:8000 `
  --dart-define=TEACHER_DASHBOARD_URL=http://localhost:3000
```

Camera OCR is mobile-only. For an Android emulator the default API URL is `http://10.0.2.2:8000`. For a physical phone, pass the computer's LAN address with `--dart-define` and ensure the backend listens on `0.0.0.0`.

Teacher mode opens the responsive Teacher Dashboard in the device's external
browser and uses a separate web login/session. Set
`TEACHER_DASHBOARD_URL` to a LAN, staging or production URL as appropriate;
staging and production must use HTTPS. No mobile token is appended to this URL.

On first use, the mobile app asks whether the learner wants self-study or to join a class with an invite code. Self-study
then resumes through goal, daily time, placement and path creation; class mode opens teacher-assigned work immediately.
Settings can switch between self-study and every joined class. The fixed curriculum is separate from the seven-day
personal task plan. Mock mode is deterministic for local testing; Gemini can generate the same validated structures when enabled.

Teacher/administrator portal:

```powershell
cd admin-dashboard
npm install
npm run dev
```

Public registration creates learners. A learner can submit a teacher application from mobile Cài đặt; an administrator reviews it in the Hồ sơ giáo viên section. Approved accounts keep the same data and can switch between learner and teacher mode from Cài đặt: the mobile app remains the learner space while the web portal creates classes, shares invite codes, assigns work and reviews submissions.

Create the first administrator from `backend` with `ADMIN_PASSWORD` and the `create-admin` CLI. Public registration intentionally creates learner accounts only.

### Role and dashboard boundary

Public registration creates learner accounts. A learner can apply to become a teacher from mobile Settings; an administrator
reviews the application before teacher access is granted. Approved teacher accounts can switch between learner and teacher
mode in mobile Settings. Learners receive and submit assignments on mobile, while teachers create classes, assign work,
review submissions and send feedback through the Teacher Dashboard web portal. The mobile Teacher mode is an overview and
handoff, not a second native implementation of the full teacher dashboard.

## Quick start with Docker

```powershell
docker compose up --build
```

This starts PostgreSQL, the API on <http://localhost:8000> and LearnMate Admin on <http://localhost:3000>. API documentation is at <http://localhost:8000/docs>.

For desktop API testing, import the versioned [Postman collection](postman/README.md).
It covers health, authentication, analyses, personalized learning paths and
administrator endpoints without storing passwords or JWTs in Git. The admin
dashboard also includes an authenticated API Console for the same backend.

Create the first Docker administrator:

```powershell
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
docker compose exec -e ADMIN_PASSWORD api python -m app.cli create-admin --email admin@example.com --display-name "LearnMate Admin"
Remove-Item Env:ADMIN_PASSWORD
```

## Verify everything

```powershell
.\scripts\check.ps1
.\scripts\release-check.ps1
```

The first command is the fast local test suite. The second additionally audits dependencies, validates workflows and Compose, builds a release-mode APK and builds both production container images.

## Configuration

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env`. Keep `AI_PROVIDER=mock` until the full application flow works. To use Gemini, set `AI_PROVIDER=gemini` and provide `GEMINI_API_KEY` only on the backend.

Production requirements:

- PostgreSQL `DATABASE_URL`.
- random `JWT_SECRET` of at least 32 characters.
- `APP_ENV=production`, `ENABLE_DEV_AUTH=false`, `AUTO_CREATE_SCHEMA=false`.
- HTTPS endpoint and explicit `ALLOWED_ORIGINS`.
- `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_SITE_URL` for the administrator web deployment.
- Android release signing secrets in GitHub.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [User flows: Mobile Learner, Mobile Teacher and Web Dashboard](docs/USER_FLOWS.md)
- [API contract](docs/API.md)
- [Testing](docs/TEST_PLAN.md)
- [Scope and limitations](docs/PROJECT_SCOPE_AND_LIMITATIONS.md)
- [Deployment and CI/CD](docs/DEPLOYMENT.md)
- [Production roadmap](docs/PRODUCTION_ROADMAP.md)
- [Git and releases](docs/GIT_WORKFLOW.md)
- [Codex and LearnMate MCP](docs/MCP.md)
- [Teacher mode and dashboard plan](plan2.md)
- [Content and implementation plan](plan.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
