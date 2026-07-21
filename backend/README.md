# LearnMate API

FastAPI service for authentication, AI analysis and learning history.

## Local commands

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000/docs> for Swagger UI.

## Quality checks

```powershell
python -m ruff check app tests
python -m pytest -q
```

## Database migrations

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic revision --autogenerate -m "describe change"
```

Production runs migrations before starting Uvicorn. `AUTO_CREATE_SCHEMA=true` exists only for tests and convenient local development.
