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

## Create the first administrator

Run migrations first, then provide the password through a temporary environment variable so it is not written into shell history:

```powershell
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
python -m app.cli create-admin --email admin@example.com --display-name "LearnMate Admin"
Remove-Item Env:ADMIN_PASSWORD
```

The command creates a new administrator or safely promotes an existing account. Public registration always creates a learner account.

## Quality checks

```powershell
python -m ruff check app tests alembic
python -m pytest -q
```

## Database migrations

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic revision --autogenerate -m "describe change"
```

Production runs migrations before starting Uvicorn. `AUTO_CREATE_SCHEMA=true` exists only for tests and convenient local development.
