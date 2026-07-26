# LearnMate API

FastAPI service for authentication, resumable onboarding, structured AI analysis, personalized seven-day learning
paths, teacher classes and learning history.

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

## Local MCP server

The development requirements include a read-only LearnMate MCP server for trusted local operator workflows. After
installing `requirements-dev.txt`, run it directly with:

```powershell
python mcp_server.py
```

Codex starts this process automatically through the repository's `.codex/config.toml`. See
[`docs/MCP.md`](../docs/MCP.md) for the available tools, MCP Inspector command, verification, and security boundary.

Learning paths are generated from the authenticated learner's recency-weighted analysis summary, validated against a
fixed schema and persisted in `learning_paths`. The pedagogical loop also includes a 20-question placement diagnostic,
resumable onboarding, daily progress, analysis-to-task links, vocabulary flashcards, teacher-owned classes and
AI-analyzed assignments. Run Alembic before starting the API so revision `0006` is applied.

## Create the first administrator

Run migrations first, then provide the password through a temporary environment variable so it is not written into shell history:

```powershell
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
python -m app.cli create-admin --email admin@example.com --display-name "LearnMate Admin"
Remove-Item Env:ADMIN_PASSWORD
```

The command creates a new administrator or safely promotes an existing account. Public registration always creates a
learner account. Administrators can assign the separate `teacher` role through `PATCH /api/v1/admin/users/{id}`.

## Quality checks

```powershell
python -m ruff check app tests alembic mcp_server.py
python -m pytest -q
```

## Database migrations

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic revision --autogenerate -m "describe change"
```

Production runs migrations before starting Uvicorn. `AUTO_CREATE_SCHEMA=true` exists only for tests and convenient local development.
