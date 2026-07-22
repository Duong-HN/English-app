---
name: authentication
description: "Implement, debug, test, or review LearnMate identity and access flows across the FastAPI backend, Flutter learner app, and administrator dashboard. Use for registration, login, JWT creation or validation, bearer propagation, token storage/restoration, logout, active-user checks, development auth, administrator RBAC, or account moderation."
---

# Authentication

## Purpose

Preserve a coherent email/password and JWT contract across all three applications while keeping authorization authoritative on the backend and tokens in the project's established client stores.

## When to use

- Changing register, login, current-profile, logout, token restore, or bearer-header behavior.
- Changing JWT claims, expiry, issuer, password handling, active-account checks, roles, or admin bootstrap.
- Debugging 401/403 responses or client session restoration.
- Reviewing any feature whose access differs for learners and administrators.

## Project-specific rules

- Authentication is custom FastAPI JWT auth; the project does not use Firebase Authentication, OAuth social login, a repository layer, or a Clean Architecture auth use case.
- Public POST /api/v1/auth/register always creates a learner. Never accept a role from the client.
- Normalize email to lowercase and query case-insensitively. Preserve the IntegrityError rollback that protects against concurrent duplicate registration.
- Hash passwords with PasswordHash.recommended from pwdlib; never store or return plaintext or password_hash.
- JWTs contain user ID in sub plus iat, exp, and iss. Decode with the configured algorithm and validate the issuer.
- On bearer-token requests, `get_current_user` loads the database user and rejects missing or inactive accounts. The non-production `X-Dev-User` branch may create and immediately return a development user before that active-state check; do not treat dev auth as production-equivalent. `require_admin` validates the server-side role of the returned user.
- X-Dev-User is only allowed when ENABLE_DEV_AUTH is true and APP_ENV is not production. Production Settings reject dev auth and weak JWT secrets.
- Create or promote the first admin through backend/app/cli.py, not public registration or a dashboard-only state change.
- Preserve self-lockout and final-active-admin protections in backend/app/routers/admin.py.
- Flutter stores the learner JWT through SecureTokenStore/FlutterSecureStorage and clears it when restored profile access returns 401.
- The admin dashboard keeps its JWT in browser sessionStorage so it disappears when the tab session ends; it revalidates with /auth/me and checks user.role.
- Both clients send Authorization: Bearer TOKEN through their central API clients, not ad hoc feature code.

## Best practices

- Treat the backend as the sole authorization authority; client role checks are user experience guards only.
- Keep invalid login responses generic so account existence is not disclosed.
- Keep the token response contract synchronized across backend schemas, Flutter AuthController/ApiClient, and AdminApi.
- Clear client token state on explicit logout and invalid restored sessions.
- Keep password bounds consistent: registration and admin creation currently require 8 to 128 characters.
- Add tests for success, invalid password, duplicate-case email, missing/invalid/expired token, inactive user, learner/admin separation, and restore/logout behavior.
- Use unique test emails because backend tests share a session-scoped SQLite database.

## Common mistakes

- Adding Firebase or a second auth stack without an explicit migration request.
- Allowing registration to choose admin role or trusting a role sent by a client.
- Decoding a JWT without validating issuer, expiry, or the allowed algorithm.
- Treating possession of an old token as sufficient after an account is disabled.
- Storing learner tokens in plain preferences or admin tokens in persistent localStorage.
- Attaching bearer tokens manually in individual screens and missing some calls.
- Returning password_hash in a response model, log, fixture, or audit entry.
- Forgetting rollback after a duplicate registration IntegrityError.
- Enabling X-Dev-User or retaining the default development secret in production.
- Testing only backend login while breaking mobile restore or admin session behavior.

## Required workflow

1. Run git status --short and trace the auth contract through backend schemas/routes/security/dependencies and both client API/session implementations.
2. Define the required identity, token, role, and failure behavior. Distinguish authentication failures (401) from insufficient admin role (403).
3. Implement password/JWT changes in backend/app/security.py and request flow changes in backend/app/routers/auth.py.
4. Update get_current_user or require_admin only when access semantics change; retain active-user database validation.
5. Update Flutter AuthController, TokenStore, and ApiClient or AdminApi/admin-app only if the wire/session contract changes.
6. Preserve the controlled backend CLI path for administrator creation and admin lockout guards.
7. Add focused backend tests plus mobile/admin tests for affected client behavior.
8. Run backend Ruff/pytest, Flutter format/analyze/test, and admin npm lint/test in proportion to the touched surfaces.
9. Check backend/.env.example, docs/API.md, docs/ARCHITECTURE.md, SECURITY.md, and Postman templates for contract changes without adding credentials.
10. Inspect the final diff for token, password, role, or learner-data leakage.

## Examples from this repository

- backend/app/routers/auth.py::register lowercases email, hashes the password, handles the uniqueness race, and returns a TokenResponse.
- backend/app/routers/auth.py::login verifies active state and password, records last-login metadata, and issues a JWT.
- backend/app/security.py::create_access_token and decode_access_token implement the expiring issuer-bound token.
- backend/app/dependencies.py::get_current_user gates development headers, rejects inactive users on the bearer-token path, and may create a development learner on the non-production header path.
- backend/app/dependencies.py::require_admin and backend/app/routers/admin.py enforce server-side RBAC and lockout protection.
- mobile/lib/src/core/token_store.dart::SecureTokenStore uses FlutterSecureStorage.
- mobile/lib/src/core/auth_controller.dart restores /auth/me, clears a rejected token, and centralizes login/register/logout state.
- mobile/lib/src/core/api_client.dart::_headers attaches the learner bearer token.
- admin-dashboard/app/admin-app.tsx restores and clears a tab-scoped sessionStorage token.
- admin-dashboard/app/lib/api.ts::AdminApi attaches the administrator bearer token.

## Files to reference

- backend/app/routers/auth.py
- backend/app/security.py
- backend/app/dependencies.py
- backend/app/config.py
- backend/app/schemas.py
- backend/app/cli.py
- backend/app/routers/admin.py
- backend/tests/test_api.py
- backend/tests/test_admin.py
- backend/tests/test_config.py
- mobile/lib/src/core/auth_controller.dart
- mobile/lib/src/core/token_store.dart
- mobile/lib/src/core/api_client.dart
- mobile/test/auth_controller_test.dart
- mobile/test/api_client_test.dart
- admin-dashboard/app/admin-app.tsx
- admin-dashboard/app/lib/api.ts
- admin-dashboard/tests/rendered-html.test.mjs
- docs/API.md
- docs/ARCHITECTURE.md
- SECURITY.md

## Files that should never be modified

- Never modify backend/.env or commit real passwords, JWTs, JWT_SECRET, Current Postman values, or copied Authorization headers.
- Never modify mobile Android/iOS signing files, secure-storage contents, browser storage snapshots, local databases, .venv, caches, or generated build output.
- Never promote an account by editing a local/prod database as part of a code task; use the CLI or tested admin API appropriate to the environment.
- Never weaken production validation merely to make local auth convenient.
- Never overwrite unrelated dirty authentication work.

## Checklist before completion

- [ ] Public registration can only create learners.
- [ ] Passwords are Argon2-hashed and never exposed.
- [ ] JWT claims, issuer, expiry, algorithm, and bearer contract remain consistent.
- [ ] Missing, invalid, inactive, learner-only, and admin cases return the intended status.
- [ ] Backend remains the authorization authority.
- [ ] Flutter secure storage and admin sessionStorage behavior remain correct.
- [ ] Restore and logout clear invalid/local session state.
- [ ] Dev auth cannot operate in production.
- [ ] Affected backend, mobile, and admin tests pass.
- [ ] No credential, token, secret, database, cache, or unrelated file changed.
