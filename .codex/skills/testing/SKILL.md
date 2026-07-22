---
name: testing
description: "Design, implement, and run LearnMate tests across FastAPI, Flutter, Vinext/Cloudflare Worker, Postman assets, migrations, containers, and CI. Use for new feature coverage, bug regressions, test failures, fixtures, fakes, quality gates, or release verification."
---

# Testing

## Purpose

Add proportionate regression coverage using the test seams and quality gates already established in each application.

## When to use

Use with every behavior change, bug fix, endpoint/schema change, refactor, dependency update, build change, or investigation of a failing gate.

## Project-specific rules

- Backend uses pytest, pytest-asyncio, FastAPI `TestClient`, and `httpx.MockTransport`; Ruff formatting and lint are separate required checks.
- Backend tests set environment variables before importing `app.db` or `app.main` because settings and the engine are module globals.
- Backend tests share a session-scoped SQLite database; use unique data and avoid exact global-count assumptions unless the fixture is deliberately reset.
- Flutter uses `flutter_test`, `package:http/testing.dart` `MockClient`, constructor-injected service fakes, and `MemoryTokenStore`; no Mockito/Mocktail is installed.
- Admin uses built-in `node:test` and `node:assert/strict`. `npm test` first builds the Vinext Worker, then tests SSR output and pure/network helpers.
- Automated tests must use Mock AI or a mocked Gemini transport; never spend real provider quota.
- Keep Postman credential/token values empty and preserve `backend/tests/test_postman_assets.py` coverage.
- There is no enforced coverage threshold. Add meaningful assertions rather than optimizing a percentage.

## Best practices

- Reproduce a bug with a focused failing test before fixing it when practical.
- Cover validation, authentication, ownership isolation, error mapping, and persistence—not only the happy path.
- Keep UI fakes behind existing interfaces such as `OcrService`, `SpeechService`, `TokenStore`, `http.Client`, and `AdminApi`/`fetch` boundaries.
- Use stable widget keys already present for learning-path interactions.
- For model/schema changes, test a clean Alembic upgrade as well as API behavior.
- Run the narrowest useful test during iteration, then the full component gate before handoff.

## Common mistakes

- Running Ruff format but not Ruff lint/import sorting.
- Setting backend test environment after importing the application.
- Calling live Gemini, camera, microphone, or production services in automated tests.
- Assuming backend per-test database rollback exists.
- Running only `node --test` and skipping the required production build in `npm test`.
- Asserting implementation text so rigidly that harmless refactors break tests, except where SSR/security contracts intentionally require source assertions.
- Forgetting negative cases for cross-user access, inactive users, admin self-lockout, malformed JSON, or missing auth.
- Editing generated test output or local database files.

## Required workflow

1. Identify the smallest observable contract that could regress.
2. Read adjacent tests and reuse their fixture/fake style.
3. Add focused success, validation/error, authorization/ownership, and persistence/UI assertions as relevant.
4. Run the focused test until it passes for the right reason.
5. Run formatting/lint/analyze before the full test suite.
6. For schema changes, upgrade a clean database to Alembic head.
7. For dependencies or release changes, add audits, builds, Compose, and container checks as required.
8. Update `docs/TEST_PLAN.md` when coverage responsibilities materially change.

## Examples from this repository

- `backend/tests/test_api.py` covers registration, duplicate handling, JWT profile access, analysis persistence, deletion, validation, and user isolation.
- `backend/tests/test_learning_paths.py` covers seven-day structure, persistence, ownership isolation, and administrator moderation.
- `backend/tests/test_ai.py` uses `httpx.MockTransport` and verifies Gemini `responseJsonSchema` plus product boundaries.
- `mobile/test/home_page_test.dart` injects fake OCR/speech adapters and verifies learning-path rendering/restoration.
- `admin-dashboard/tests/rendered-html.test.mjs` imports the built Worker and verifies the server-rendered Vietnamese login.
- `admin-dashboard/tests/api-console.test.mjs` checks safe cURL output and authenticated encoded API requests.

## Files to reference

- `docs/TEST_PLAN.md`
- `scripts/check.ps1`
- `scripts/release-check.ps1`
- `.github/workflows/ci.yml`
- `backend/pyproject.toml`
- `backend/tests/`
- `mobile/analysis_options.yaml`
- `mobile/test/`
- `admin-dashboard/package.json`
- `admin-dashboard/tests/`

## Files that should never be modified

- Never commit or hand-edit test databases, coverage output, `dist/`, `build/`, caches, `.venv/`, `.dart_tool/`, or `node_modules/`.
- Never put real secrets, JWTs, learner content, or live provider credentials into fixtures.
- Never weaken production validation or authorization merely to make a test pass.
- Never rewrite unrelated existing tests or user work without a behavior reason.

## Checklist before completion

- [ ] A focused regression test covers the requested behavior.
- [ ] Failure, validation, auth/ownership, and cleanup cases are covered where relevant.
- [ ] External services and device capabilities are faked deterministically.
- [ ] Format/lint/analyze and the full affected component suite pass.
- [ ] Migration, build, audit, or container gates were run when the change requires them.
- [ ] Any pre-existing failure is separated clearly from failures introduced by the change.
