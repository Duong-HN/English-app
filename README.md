# LearnMate AI

LearnMate AI is a graduation-project MVP for formative English learning. It combines a Flutter mobile application, an administrator web console, on-device OCR, speech-to-text, a FastAPI backend, PostgreSQL/SQLite and a replaceable AI provider.

> AI feedback and scores are formative. The application does not claim to provide an official IELTS score or infer pronunciation quality from a transcript.

## Implemented

- Email/password registration and JWT login.
- Secure token storage on the device.
- Administrator RBAC, account moderation and immutable audit logs.
- Responsive web dashboard with live metrics, user/content management and an authenticated API Console.
- Reading analysis with translation, vocabulary and questions.
- Writing feedback with issues, score and rewrite.
- Speaking transcript feedback for relevance, grammar and vocabulary.
- Camera/gallery OCR on Android and iOS using on-device ML Kit.
- Device speech-to-text for English transcripts.
- Per-user persisted history and deletion.
- SQLite development mode and PostgreSQL production support.
- Alembic database migrations.
- Deterministic Mock AI and optional Gemini adapter with structured output validation.
- Backend, administrator web and Flutter automated tests.
- Docker Compose for PostgreSQL, API and admin web; GitHub Actions CI, signed APK release, GHCR images and deployment hooks.

## Architecture

```text
Flutter mobile                              Admin web
  ├─ secure auth token                        ├─ operations dashboard
  ├─ camera -> OCR -> editable text           └─ authenticated API Console
  └─ microphone -> STT transcript                       |
                 |                                      |
                 +----------> FastAPI REST API <---------+
                                   |
                         +---------+---------+
                         v                   v
                 PostgreSQL/SQLite    Mock AI or Gemini
```

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
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

Camera OCR is mobile-only. For an Android emulator the default API URL is `http://10.0.2.2:8000`. For a physical phone, pass the computer's LAN address with `--dart-define` and ensure the backend listens on `0.0.0.0`.

Administrator web:

```powershell
cd admin-web
npm install
npm run dev
```

Create the first administrator from `backend` with `ADMIN_PASSWORD` and the `create-admin` CLI. Public registration intentionally creates learner accounts only.

## Quick start with Docker

```powershell
docker compose up --build
```

This starts PostgreSQL, the API on <http://localhost:8000> and LearnMate Admin on <http://localhost:3000>. API documentation is at <http://localhost:8000/docs>.

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
- [API contract](docs/API.md)
- [Testing](docs/TEST_PLAN.md)
- [Deployment and CI/CD](docs/DEPLOYMENT.md)
- [Git and releases](docs/GIT_WORKFLOW.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
