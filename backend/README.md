# LearnMate API

FastAPI service for authentication, resumable onboarding, isolated self/class learning spaces, structured AI analysis,
fixed curriculum content, personalized seven-day learning paths, teacher classes and learning history.

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

Learning paths are generated from the active self-learning space's recency-weighted analysis summary, validated against
a fixed schema and persisted in `learning_paths`. Joined classes receive their own learning space; class assignments,
analyses and progress never feed back into self-study or another class. The pedagogical loop also includes a
20-question placement diagnostic, a focused English A2→B1 lesson pack, IELTS band course metadata, resumable onboarding,
daily progress, vocabulary flashcards, teacher-owned classes and AI-analyzed assignments. Run Alembic before starting
the API so the latest Alembic revisions are applied. Lesson audio/video binaries are kept outside the database under
`MEDIA_STORAGE_DIR`; use the administrator's curriculum media screen to upload owned/licensed assets or register an
HTTPS CDN URL. The A2→B1 pack also documents three original video recording scripts under
[`app/content/README.md`](app/content/README.md). `MEDIA_MAX_SIZE_MB` defaults to 100. The legacy
`POST /api/v1/analyses/{type}` endpoint is a compatibility alias that also returns `202` with an analysis job. Clients
can submit `POST /api/v1/analysis-jobs/{type}`, poll `GET /api/v1/analysis-jobs/{job_id}`, and run
`python -m app.worker` as a separate process. The job boundary supports idempotency keys, PostgreSQL-safe claiming and
bounded retries, but remains a database-backed prototype queue until managed queue infrastructure is introduced.

## Create the first administrator

Run migrations first, then provide the password through a temporary environment variable so it is not written into shell history:

```powershell
$env:ADMIN_PASSWORD = "replace-with-a-strong-password"
python -m app.cli create-admin --email admin@example.com --display-name "LearnMate Admin"
Remove-Item Env:ADMIN_PASSWORD
```

The command creates a new administrator or safely promotes an existing account. Public registration always creates a
learner account. Learners submit teacher applications through `POST /api/v1/teacher-applications`; administrators
approve or reject them through `PATCH /api/v1/admin/teacher-applications/{id}`. Direct learner-to-teacher role changes
are rejected so every teacher account has an auditable approval record. After approval, a teacher keeps access to the
learner APIs and can use the same account in either learner or teacher mode; submitting a new teacher application
remains learner-only.

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
