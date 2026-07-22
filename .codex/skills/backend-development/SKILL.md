---
name: backend-development
description: "Develop, debug, review, or refactor the LearnMate Python backend. Use for FastAPI routes, Pydantic contracts, middleware, settings, CLI commands, dependency wiring, backend feature orchestration, HTTP behavior, or changes under backend/app, backend/tests, and backend/alembic."
---

# Backend Development

## Purpose

Make backend changes that fit LearnMate's existing FastAPI and SQLAlchemy design, preserve its API and security boundaries, and remain testable in SQLite and deployable with PostgreSQL.

## When to use

- Adding or changing FastAPI endpoints, request/response schemas, middleware, health checks, settings, or CLI commands.
- Debugging backend validation, HTTP status, dependency, persistence, or provider-orchestration behavior.
- Refactoring backend modules or reviewing a backend pull request.
- Coordinating a backend feature across models, schemas, routers, tests, migrations, configuration, and documentation.

## Project-specific rules

- Treat backend/app as a pragmatic modular monolith. Routers call SQLAlchemy directly; this repository has no Repository Pattern, Clean Architecture use-case layer, DI container, or Firebase backend.
- Target Python 3.14 and the pinned dependencies in backend/requirements.txt. Follow backend/pyproject.toml: Ruff target py314, line length 110, rules E/F/I/B/UP, with B008 ignored for FastAPI Depends defaults.
- Put HTTP contracts in backend/app/schemas.py and AI-only contracts in backend/app/ai_schemas.py. Use Pydantic v2 validators and ConfigDict(from_attributes=True) for ORM responses.
- Define a feature APIRouter with its feature prefix and tags, then mount it under /api/v1 in backend/app/main.py. Health routes remain unversioned.
- Declare response_model and deliberate status codes. Existing semantics are 422 validation, 401 authentication, 403 authorization, 404 ownership-safe absence, 409 conflicts, and 502 sanitized AI failures.
- Inject Settings, Session, current user, and admin authorization with FastAPI Depends through backend/app/config.py, db.py, and dependencies.py.
- Keep learner resources ownership-scoped with a user_id == current user filter on list, read, and delete operations. Admin routes must use require_admin.
- Use async handlers only when awaiting async work such as an AI provider. Existing database sessions are synchronous.
- Remember that settings and the SQLAlchemy engine are initialized at import time. Tests must set environment variables before importing app.db or app.main.
- Preserve the current privacy product boundary: feedback is formative, transcript text is not pronunciation evidence, and historical learning-path personalization uses aggregates.

## Best practices

- Trace a feature end to end before editing: schema, router, dependency, model, migration, provider, client contract, test, and documentation.
- Use modern type annotations, relative imports inside app, bounded Field/Query inputs, and UTC timestamps through models.utc_now.
- Return Pydantic response objects rather than leaking ORM internals or sensitive columns.
- Keep provider exceptions behind a stable, generic HTTP response and retain the original exception as the cause.
- Add focused tests for success, invalid input, unauthenticated access, ownership isolation, and relevant admin behavior.
- Keep changes narrow. Check the dirty worktree first and work around unrelated modified or untracked files.

## Common mistakes

- Inventing repository, use-case, service-container, or Firebase abstractions that the project does not use.
- Adding a router file but forgetting to import and include it in backend/app/main.py.
- Returning ad hoc dictionaries that drift from backend/app/schemas.py.
- Omitting the authenticated owner filter or trusting a client-provided role.
- Setting test environment variables after importing the application.
- Updating an ORM model without an Alembic revision.
- Relying on Base.metadata.create_all in production; production runs Alembic with AUTO_CREATE_SCHEMA=false.
- Running Ruff formatting but skipping Ruff lint/import sorting.
- Changing a documented endpoint without updating clients, Postman assets, and docs/API.md.

## Required workflow

1. Run git status --short and inspect all related files and tests. Preserve existing dirty and untracked work.
2. Trace the closest existing flow. Use analyses for learner-owned CRUD, learning_paths for AI-plus-persistence, auth for registration/login, and admin for privileged operations.
3. Define or update validated request and response contracts before implementing route behavior.
4. Implement through existing FastAPI dependencies and direct SQLAlchemy 2 queries. Add a model and new migration only when persistence changes.
5. Mount new routers and update backend/.env.example only when a new non-secret setting is introduced.
6. Add focused tests. Use the deterministic Mock AI and HTTP transports rather than live external services.
7. Run from backend:
   - python -m ruff format --check app tests alembic
   - python -m ruff check app tests alembic
   - python -m pytest -q
8. For schema changes, run a clean python -m alembic upgrade head with AUTO_CREATE_SCHEMA=false.
9. Update backend/README.md, docs/API.md, docs/ARCHITECTURE.md, docs/TEST_PLAN.md, and CHANGELOG.md when their contracts or claims change.
10. Recheck git diff --check and git status --short; verify only intended files changed.

## Examples from this repository

- backend/app/routers/analyses.py shows authenticated create/list/get/delete behavior with ownership filters and a sanitized 502 for AI failures.
- backend/app/routers/learning_paths.py::_activity_profile and generate_learning_path show bounded recent-history aggregation, provider orchestration, persistence, and a user profile update.
- backend/app/routers/admin.py::update_user shows server-side RBAC, lockout guards, audit recording, and a single commit.
- backend/app/routers/auth.py::register shows Pydantic input, case-insensitive duplicate detection, Argon2 hashing, IntegrityError rollback, and a typed token response.
- backend/app/main.py::create_app is the router and middleware composition root.

## Files to reference

- backend/app/main.py
- backend/app/config.py
- backend/app/db.py
- backend/app/dependencies.py
- backend/app/schemas.py
- backend/app/models.py
- backend/app/routers/
- backend/tests/conftest.py
- backend/tests/test_api.py
- backend/tests/test_admin.py
- backend/tests/test_learning_paths.py
- backend/pyproject.toml
- backend/README.md
- docs/API.md
- docs/ARCHITECTURE.md
- .github/workflows/ci.yml

## Files that should never be modified

- Never modify backend/.env or place a real secret in any tracked file.
- Never modify generated/local artifacts: backend/.venv/, backend/*.db, backend/tests/*.db, __pycache__/, .pytest_cache/, .ruff_cache/, or *.pyc.
- Never rewrite an Alembic revision that has already been applied or released; create the next revision. Inspect `git status` and preserve whatever unrelated migration work is actually present.
- Never overwrite unrelated dirty files or use destructive Git cleanup.
- Do not edit generated OpenAPI output; FastAPI produces it at runtime.

## Checklist before completion

- [ ] The change follows the modular FastAPI/direct-ORM architecture without invented layers.
- [ ] Request, response, status, auth, and ownership behavior are explicit.
- [ ] New routers are mounted and new settings are documented without secrets.
- [ ] Persistence changes include a reviewed new migration.
- [ ] Focused tests cover failures and isolation as well as success.
- [ ] Ruff format, Ruff lint, pytest, and any required migration check pass.
- [ ] API and architecture documentation match the implementation.
- [ ] No secret, database, cache, historical migration, or unrelated dirty file was changed.
