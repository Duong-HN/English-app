# LearnMate AI

LearnMate AI is a graduation-project MVP for formative English learning. It combines a Flutter mobile application, on-device OCR, speech-to-text, a FastAPI backend, PostgreSQL/SQLite and a replaceable AI provider.

> AI feedback and scores are formative. The application does not claim to provide an official IELTS score or infer pronunciation quality from a transcript.

## Implemented

- Email/password registration and JWT login.
- Secure token storage on the device.
- Reading analysis with translation, vocabulary and questions.
- Writing feedback with issues, score and rewrite.
- Speaking transcript feedback for relevance, grammar and vocabulary.
- Camera/gallery OCR on Android and iOS using on-device ML Kit.
- Device speech-to-text for English transcripts.
- Per-user persisted history and deletion.
- SQLite development mode and PostgreSQL production support.
- Alembic database migrations.
- Deterministic Mock AI and optional Gemini adapter with structured output validation.
- Backend and Flutter automated tests.
- Docker, GitHub Actions CI, signed APK release workflow, GHCR image publishing and optional CD hook.

## Architecture

```text
Flutter mobile
  ├─ secure auth token
  ├─ camera -> on-device OCR -> editable text
  └─ microphone -> STT transcript
          |
          v
FastAPI REST API -> PostgreSQL/SQLite
          |
          └─ Mock AI (test/dev) or Gemini (server-side key)
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

## Quick start with Docker

```powershell
docker compose up --build
```

This starts PostgreSQL and the API on <http://localhost:8000>. API documentation is at <http://localhost:8000/docs>.

## Verify everything

```powershell
.\scripts\check.ps1
.\scripts\release-check.ps1
```

The first command is the fast local test suite. The second additionally audits dependencies, validates workflows and Compose, builds a release-mode APK and builds the production container image.

## Configuration

Copy [`backend/.env.example`](backend/.env.example) to `backend/.env`. Keep `AI_PROVIDER=mock` until the full application flow works. To use Gemini, set `AI_PROVIDER=gemini` and provide `GEMINI_API_KEY` only on the backend.

Production requirements:

- PostgreSQL `DATABASE_URL`.
- random `JWT_SECRET` of at least 32 characters.
- `APP_ENV=production`, `ENABLE_DEV_AUTH=false`, `AUTO_CREATE_SCHEMA=false`.
- HTTPS endpoint and explicit `ALLOWED_ORIGINS`.
- Android release signing secrets in GitHub.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API contract](docs/API.md)
- [Testing](docs/TEST_PLAN.md)
- [Deployment and CI/CD](docs/DEPLOYMENT.md)
- [Git and releases](docs/GIT_WORKFLOW.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
