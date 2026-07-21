# LearnMate AI

LearnMate AI is a Flutter mobile MVP for learning English with OCR and an LLM-backed learning assistant.

## Current release

`v0.2.0-vertical` is a runnable text-first vertical slice:

```text
Flutter app -> FastAPI -> SQLite -> Mock AI -> structured result/history
```

OCR, real authentication and pronunciation assessment are deliberately isolated as the next phases. The development identity header and Mock AI must not be shipped to real users.

## Run

Terminal 1:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Terminal 2:

```powershell
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

For an Android emulator use the default `http://10.0.2.2:8000`; for a physical phone use the computer's LAN IP.

## Verify

```powershell
flutter analyze
flutter test
cd backend
pytest -q
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md) and [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md).
