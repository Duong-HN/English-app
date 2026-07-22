---
name: project-architecture
description: "Map and evolve the actual LearnMate AI monorepo architecture. Use when planning a feature, deciding file placement, coordinating backend/mobile/admin changes, assessing architectural impact, or checking whether a proposed pattern already exists."
---

# Project Architecture

## Purpose

Plan changes against the repository's real three-application architecture and keep cross-stack behavior aligned.

## When to use

Use for new features, architectural decisions, cross-application changes, major dependency additions, or any task that might touch more than one of `backend/`, `mobile/`, and `admin-dashboard/`.

## Project-specific rules

- Treat this as a pragmatic monorepo: FastAPI owns identity, business rules, AI orchestration, and persistence; Flutter is the learner client; Vinext/React is the administrator client.
- Keep each application responsible for its own source, dependencies, tests, and Docker/platform configuration. Keep shared automation and documentation at the root.
- Follow the existing feature/core organization. This repository does not implement Clean Architecture, Repository Pattern, a service layer, or a DI container.
- Keep server data in SQLAlchemy/PostgreSQL or SQLite. Mobile persists only its access token; the dashboard has no active D1, Drizzle, R2, or Firebase layer.
- Use the FastAPI REST boundary for both clients. Never call Gemini or the database directly from Flutter or the administrator dashboard.
- Treat `docs/ARCHITECTURE.md`, current code, tests, and configuration as runtime truth. Treat `ideal.md` as an academic proposal/history; its Firebase and Cloud Functions plan is not the implemented architecture.
- Preserve formative-learning boundaries: no official IELTS claim and no pronunciation inference from an STT transcript.
- Inspect `git status --short` before editing and preserve unrelated tracked and untracked work.

## Best practices

- Trace a vertical slice from Pydantic contract through route, persistence/provider, client adapter, UI, tests, and docs before choosing files.
- Prefer extending current modules and constructor/dependency seams over adding a new architectural framework.
- Keep versions and user-facing documentation coherent across `backend/app/config.py`, `backend/.env.example`, `mobile/pubspec.yaml`, `admin-dashboard/package.json`, and `CHANGELOG.md` when preparing a release feature.
- Add an architecture migration only when the request requires it and document the new boundary explicitly.
- Keep generated outputs, local state, and vendor trees outside design decisions.

## Common mistakes

- Creating repository, use-case, domain, or Firebase layers because a generic template suggests them.
- Mistaking empty `admin-dashboard/db/`, `drizzle/`, or `examples/d1/` folders and an unused Worker `DB` type for active persistence.
- Calling the administrator app a conventional Next.js Node server; it uses Next App Router syntax through Vinext/Vite and a Cloudflare Worker.
- Assuming every Flutter platform scaffold is a supported product target; OCR is deliberately Android/iOS-only.
- Updating one client contract without the backend, the other affected client, tests, Postman assets, and docs.
- Replacing direct project patterns with a large framework during an otherwise narrow feature.

## Required workflow

1. Run `git status --short` and inventory the affected application boundaries.
2. Read the nearest implementation, tests, and canonical documentation.
3. Write down the end-to-end contract, ownership/security rules, persistence needs, and UI states.
4. Implement the smallest coherent vertical slice in the owning modules.
5. Update every affected client adapter/type and focused test.
6. Update API, architecture, testing, deployment, component README, and changelog material as applicable.
7. Run the focused application gates, then `scripts/check.ps1` for cross-stack changes.
8. Review the final diff for unrelated edits, generated files, secrets, and version drift.

## Examples from this repository

- Personalized learning paths form a complete slice: `backend/app/routers/learning_paths.py`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/ai_schemas.py`, `backend/alembic/versions/0003_learning_paths.py`, `mobile/lib/src/core/api_client.dart`, `mobile/lib/src/features/home/home_page.dart`, `admin-dashboard/app/lib/api.ts`, tests, Postman, and docs.
- Authentication flows through `backend/app/routers/auth.py` and `backend/app/dependencies.py`, then `mobile/lib/src/core/auth_controller.dart` and `admin-dashboard/app/admin-app.tsx`.
- Shared delivery is coordinated by `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and `.github/workflows/deploy.yml`.

## Files to reference

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/TEST_PLAN.md`
- `docs/DEPLOYMENT.md`
- `backend/app/main.py`
- `mobile/lib/src/app.dart`
- `admin-dashboard/app/page.tsx`
- `docker-compose.yml`
- `.github/workflows/ci.yml`

## Files that should never be modified

- Never edit secrets or local credentials: `backend/.env`, keystores, `mobile/android/key.properties`, Postman Current values, or local environment files.
- Never edit generated/vendor/state trees: `node_modules/`, `dist/`, `.vinext/`, `.wrangler/`, `mobile/build/`, `.dart_tool/`, `.venv/`, caches, or local `*.db` files.
- Never hand-edit Flutter generated plugin registrants, `mobile/.metadata`, or generated lockfile internals.
- Never rewrite an applied/released Alembic revision; create the next revision.
- Never modify unrelated existing work merely to make a task easier.

## Checklist before completion

- [ ] The change lives in the component that owns the responsibility.
- [ ] No unimplemented architecture is described as current.
- [ ] Backend, clients, persistence, tests, and docs agree on the contract.
- [ ] Authentication, ownership, privacy, and AI product boundaries are preserved.
- [ ] Generated, secret, and unrelated files are untouched.
- [ ] Focused checks and the appropriate cross-stack gate pass, or pre-existing failures are reported precisely.
