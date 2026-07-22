---
name: api-integration
description: "Implement and maintain LearnMate REST contracts across FastAPI, Flutter, the Vinext administrator dashboard, Postman, and documentation. Use for endpoints, payloads, response types, error handling, pagination, authentication headers, base URLs, or client networking changes."
---

# API Integration

## Purpose

Keep the backend contract and every consuming client synchronized without bypassing established networking boundaries.

## When to use

Use when adding or changing an endpoint, request/response field, HTTP status, query filter, client method, Postman request, timeout, or API error behavior.

## Project-specific rules

- Keep health routes unversioned and application routes under `/api/v1`.
- Define backend inputs and outputs with Pydantic in `backend/app/schemas.py` or `backend/app/ai_schemas.py`; give normal routes explicit response models.
- Mount new feature routers in `backend/app/main.py` and consider static-versus-parameter route ordering.
- Keep learner queries scoped by the authenticated `user.id`; keep administrator routes behind `require_admin`.
- Preserve snake_case JSON. Flutter currently transports `Map<String, dynamic>`; the dashboard mirrors schemas with TypeScript types in `admin-dashboard/app/lib/api.ts`.
- Route mobile calls through `ApiClient` and dashboard calls through `AdminApi`; do not scatter raw networking through widgets/components.
- Register and login must not send Bearer headers. Protected calls must send `Authorization: Bearer <token>`.
- Preserve status semantics: `422` validation, `401` authentication, `403` authorization, ownership-safe `404`, `409` conflict, and `502` upstream AI failure.
- Configure mobile URLs with `--dart-define=API_BASE_URL`; configure dashboard URLs with public `NEXT_PUBLIC_API_BASE_URL`. Never hard-code a production host.
- Keep dashboard Console requests same-origin, inspectable on non-2xx, and token-redacted in cURL/history. Regular `AdminApi` requests should throw `ApiError` on non-2xx.

## Best practices

- Change the backend schema first, then update both client adapters/types before UI code.
- Bound query parameters and use backend pagination rather than loading entire tables.
- Convert FastAPI string or validation-list details into readable client errors without exposing internals.
- Test HTTP behavior with FastAPI `TestClient`, Dart `MockClient`, Node's stubbed `fetch`, and `httpx.MockTransport` for Gemini.
- Keep `docs/API.md`, `admin-dashboard/app/lib/api-console.ts`, and `postman/` assets aligned with public contract changes.
- Keep browser CORS origins and deploy-time public URLs synchronized.

## Common mistakes

- Updating a Pydantic model without updating TypeScript/Dart consumers.
- Adding authorization to login/register or forgetting it on protected endpoints.
- Making direct Gemini requests from either client.
- Returning an unvalidated provider dictionary or persisting it before validation.
- Trusting a frontend role or user ID.
- Removing the API Console origin check or recording request bodies/tokens in its history.
- Using a Docker service hostname for `NEXT_PUBLIC_API_BASE_URL`; the browser must reach the value.
- Assuming all response bodies are objects without testing malformed or non-JSON responses.

## Required workflow

1. Inspect `docs/API.md`, the target router/schema, both client adapters, and existing contract tests.
2. Specify method, path, auth, request, response, status codes, bounds, and ownership rules.
3. Implement and register the FastAPI route with validation and safe error mapping.
4. Update `mobile/lib/src/core/api_client.dart` and/or `admin-dashboard/app/lib/api.ts` as consumers require.
5. Update feature UI states without adding direct network calls.
6. Add backend, Dart, and admin tests at every affected boundary.
7. Update API Console presets and `postman/` requests/tests when the endpoint is part of the supported workspace.
8. Update `docs/API.md` and related architecture/deployment docs.
9. Run Ruff/pytest, Flutter format/analyze/test, and admin lint/test as applicable.

## Examples from this repository

- `POST /api/v1/learning-paths/generate` is declared in `backend/app/routers/learning_paths.py`, constrained by `LearningPathGenerateRequest`, and consumed by `ApiClient.generateLearningPath()`. The administrator adapter separately consumes `GET /api/v1/admin/learning-paths` through `AdminApi.learningPaths()`.
- `backend/app/routers/analyses.py` demonstrates ownership-safe CRUD and generic `502` mapping around a provider.
- `admin-dashboard/app/lib/api.ts` distinguishes normal typed requests from the safe, same-origin API Console pipeline.
- `mobile/lib/src/core/api_client.dart` demonstrates a 30-second timeout, conditional Bearer header, JSON decoding, and FastAPI validation-detail extraction.

## Files to reference

- `docs/API.md`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/app/routers/`
- `mobile/lib/src/core/api_client.dart`
- `mobile/test/api_client_test.dart`
- `admin-dashboard/app/lib/api.ts`
- `admin-dashboard/app/lib/api-console.ts`
- `admin-dashboard/tests/api-console.test.mjs`
- `postman/collections/LearnMate AI API.postman_collection.json`
- `backend/tests/test_postman_assets.py`

## Files that should never be modified

- Never place real tokens, passwords, API keys, or learner submissions in committed Postman values, presets, tests, logs, or docs.
- Never edit `backend/.env`, local Postman Current values, or deployed secret configuration.
- Never hand-edit generated output such as `admin-dashboard/dist/`, Flutter build output, caches, or package-manager internals.
- Never bypass server authorization by changing only a client-side role check.
- Never overwrite unrelated working-tree changes.

## Checklist before completion

- [ ] Method, path, payload, types, status codes, and auth agree across all consumers.
- [ ] Learner ownership and administrator authorization are server-enforced.
- [ ] Base URL, timeout, CORS, and error behavior match the deployment model.
- [ ] API Console and Postman artifacts remain safe and synchronized.
- [ ] Focused backend/client contract tests cover success and failure.
- [ ] `docs/API.md` reflects the implemented contract.
