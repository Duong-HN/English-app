---
name: security
description: "Threat-model, implement, review, or test LearnMate security and privacy controls. Use for secrets, authentication or authorization boundaries, CORS and headers, learner data, AI safety, audit logs, token storage, API Console or Postman safety, dependency auditing, containers, production configuration, or security-sensitive deployment changes."
---

# Security

## Purpose

Protect learner data, credentials, privileged operations, and AI trust boundaries across the FastAPI backend, Flutter app, administrator dashboard, Postman workspace, and delivery pipeline.

## When to use

- Handling passwords, JWTs, API keys, environment variables, browser/mobile token storage, or signing material.
- Adding a learner-owned or administrator operation, audit event, CORS origin, HTTP header, or API Console capability.
- Changing AI prompts/data sharing, logging, persistence, deletion, dependency versions, containers, CI, or production configuration.
- Reviewing a suspected vulnerability, privacy leak, authorization bypass, or unsafe operational instruction.

## Project-specific rules

- The FastAPI backend is the trust and authorization boundary. UI checks never replace get_current_user, require_admin, and ownership-scoped database queries.
- This is a pragmatic modular monolith with direct ORM access. It has no Firebase security rules, Repository Pattern, or Clean Architecture policy layer.
- Passwords use Argon2 through pwdlib; JWTs are expiring and issuer-bound; production requires a random JWT secret of at least 32 characters.
- Production must set APP_ENV=production, ENABLE_DEV_AUTH=false, AUTO_CREATE_SCHEMA=false, explicit HTTPS ALLOWED_ORIGINS, and server-side Gemini credentials.
- Keep X-Dev-User unavailable in production.
- Flutter learner tokens belong in FlutterSecureStorage. Admin browser tokens remain tab-scoped in sessionStorage, not persistent localStorage.
- Admin roles are granted through the backend CLI or server-authorized admin API. Preserve self-lockout/final-active-admin guards.
- Keep admin audit logs append-only through public APIs. Record identifiers and change summaries, never passwords, tokens, or full learner submissions.
- Learner analysis and learning-path operations must always filter by current user ID; ownership-safe absence returns 404.
- Never describe transcript feedback as pronunciation evidence or AI output as an official exam score.
- Send only aggregate historical activity to the learning-path provider; do not disclose full prior submissions.
- Preserve main.py security headers and explicit CORS methods/headers. Do not broaden origins to wildcard while credentials are enabled.
- Postman committed environments keep password/token values empty. API Console history and cURL export must not persist live secrets.
- Docker runs the backend as a non-root user; CI audits production Python/Node dependencies and Dependabot checks ecosystems weekly.

## Best practices

- Start with data flow and authority: identify input, caller, authenticated principal, owner, privileged actor, storage, logs, external recipient, and deletion path.
- Deny by default and validate authorization on every backend request, including reads and deletes.
- Minimize data sent to AI providers, audit records, logs, tests, screenshots, and documentation.
- Use generic authentication/provider errors and avoid echoing sensitive upstream bodies.
- Keep secrets in environment/secret stores and placeholders in tracked examples.
- Add negative tests for unauthenticated, wrong-user, learner-on-admin, disabled-user, self-lockout, and final-admin cases.
- Retain dependency pinning and run pip-audit/npm audit when dependency or release security is in scope.
- Document residual risks honestly. `SECURITY.md` requires managed PostgreSQL backups, gateway rate limits/cost alerts, and retention rules; `docs/ARCHITECTURE.md` separately identifies password reset/email verification as future work.

## Common mistakes

- Trusting role, user ID, resource owner, or API base URL supplied by a client.
- Adding a frontend-only admin guard without require_admin.
- Using wildcard CORS with credentials or exposing X-Dev-User in production.
- Logging request bodies, bearer headers, password fields, Gemini keys, or provider payloads.
- Persisting admin JWTs in localStorage or learner JWTs in plain preferences.
- Copying live Postman Current values, cURL tokens, .env files, or signing keys into Git.
- Recording full learner text in AdminAuditLog.details.
- Sending historical input_text values to Gemini for personalization.
- Weakening TLS/secret checks or container user permissions to simplify deployment.
- Claiming unimplemented protections such as rate limiting, reset flows, observability, or retention enforcement.
- Treating dependency scanning as a replacement for authorization and privacy review.

## Required workflow

1. Run git status --short and read SECURITY.md, docs/ARCHITECTURE.md security boundaries, and the concrete code paths involved.
2. Map principals, assets, trust boundaries, storage, external services, logs, failure responses, and deletion behavior.
3. Verify backend authentication, active-account validation, RBAC, and owner filters before considering client controls.
4. Apply least privilege, input bounds, data minimization, sanitized errors, and safe secret/config handling.
5. Preserve or extend audit coverage for privileged mutations without copying sensitive content.
6. Add negative security tests on every affected surface. Use fake tokens/providers and empty Postman credentials.
7. Run relevant backend, Flutter, admin, dependency-audit, migration, and container checks in proportion to risk.
8. Review tracked configuration, Postman assets, logs, test fixtures, docs, and git diff for accidental secrets or personal data.
9. Update SECURITY.md and deployment documentation when controls or known limitations change.
10. Report residual risks separately from implemented guarantees.

## Examples from this repository

- backend/app/config.py::validate_production_secrets rejects weak JWT secrets and development authentication in production.
- backend/app/security.py hashes passwords and validates issuer-bound JWTs.
- backend/app/dependencies.py checks active users on the bearer-token path and server-side admin roles; its gated non-production dev-header branch returns before the active-state check.
- backend/app/routers/analyses.py and learning_paths.py include authenticated owner filters.
- backend/app/routers/admin.py::_ensure_another_active_admin and update_user prevent administrator lockout and append audit records.
- backend/app/main.py configures explicit credentialed CORS and nosniff, frame-deny, no-referrer, and no-store headers.
- mobile/lib/src/core/token_store.dart uses FlutterSecureStorage.
- admin-dashboard/app/admin-app.tsx uses sessionStorage and revalidates the token with /auth/me.
- backend/tests/test_postman_assets.py verifies committed Postman credentials and tokens are empty.
- backend/Dockerfile creates and runs as the non-root learnmate user.
- .github/workflows/ci.yml runs pip-audit and npm audit; .github/dependabot.yml schedules weekly updates.

## Files to reference

- SECURITY.md
- docs/ARCHITECTURE.md
- docs/DEPLOYMENT.md
- backend/app/config.py
- backend/app/security.py
- backend/app/dependencies.py
- backend/app/main.py
- backend/app/routers/auth.py
- backend/app/routers/analyses.py
- backend/app/routers/learning_paths.py
- backend/app/routers/admin.py
- backend/app/models.py
- backend/tests/test_config.py
- backend/tests/test_api.py
- backend/tests/test_admin.py
- backend/tests/test_learning_paths.py
- backend/tests/test_postman_assets.py
- mobile/lib/src/core/token_store.dart
- mobile/lib/src/core/auth_controller.dart
- admin-dashboard/app/admin-app.tsx
- admin-dashboard/app/lib/api.ts
- admin-dashboard/app/lib/api-console.ts
- postman/environments/LearnMate Local.postman_environment.json
- backend/Dockerfile
- docker-compose.yml
- .github/workflows/ci.yml
- .github/dependabot.yml

## Files that should never be modified

- Never modify or commit backend/.env, real Postman Current values, access tokens, passwords, GEMINI_API_KEY, JWT_SECRET, deployment hook URLs, signing keys, keystores, or mobile/android/key.properties.
- Never modify local databases, secure/browser storage artifacts, backend/.venv/, node_modules/, build outputs, caches, bytecode, or generated coverage.
- Never rewrite applied migrations or erase audit records to make a test or demo pass.
- Never weaken a production control or broaden access without explicit authorization and documented risk.
- Never overwrite unrelated dirty work or expose learner content while inspecting failures.

## Checklist before completion

- [ ] Backend authentication, active-user validation, RBAC, and owner checks are authoritative.
- [ ] Secrets and tokens remain in approved stores and absent from tracked files/logs.
- [ ] CORS, security headers, production config validation, and non-root execution remain safe.
- [ ] Admin mutations are guarded and audited without sensitive payloads.
- [ ] AI claims and historical data sharing respect documented limits.
- [ ] Negative tests cover unauthorized, wrong-owner, disabled, and wrong-role cases.
- [ ] Relevant audits and build/test gates pass.
- [ ] Documentation distinguishes implemented controls from residual risks.
- [ ] No secret, learner data, local artifact, historical migration, audit record, or unrelated dirty file changed.
