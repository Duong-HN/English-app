# Changelog

All notable changes to LearnMate AI are recorded here.

## 0.6.0 - 2026-07-21

### Added

- FastAPI administrator RBAC, searchable operational APIs, account lockout protection and audit logs.
- Administrator CLI for safely creating or promoting the first admin account.
- Responsive LearnMate Admin web with JWT login, live metrics, user management and analysis moderation.
- Authenticated API Console with endpoint presets, response timing, safe session history and cURL export.
- Admin web lint/build/tests, production Docker image, Compose service, GHCR release image and deployment hook.

### Changed

- CI/CD now validates and packages mobile, backend and administrator web as one release unit.
- Local Compose CORS supports both `localhost` and `127.0.0.1` development origins.

### Security

- Admin authorization is enforced server-side; the web dashboard cannot grant its own privileges.
- JWTs stay in tab-scoped `sessionStorage`; API Console history excludes request bodies and tokens.
- API Console rejects cross-origin request paths and cURL export uses an environment placeholder instead of the live token.

## 0.5.0 - 2026-07-21

### Added

- Flutter registration, JWT login, secure session storage and per-user history.
- On-device Latin OCR from camera/gallery and English speech-to-text.
- Structured reading, writing and transcript feedback with Mock/Gemini providers.
- FastAPI authentication, PostgreSQL support, Alembic migrations and production checks.
- Backend and Flutter automated tests, Docker packaging, CI, signed APK release and CD hook workflows.
- Architecture, API, testing, deployment and security documentation.

### Security

- Argon2 password hashing, expiring JWTs and user-isolated database queries.
- Production secret validation, non-root API container and automated dependency auditing.
- Explicitly excludes pronunciation claims when only a transcript is available.

### Fixed

- Android release shrinking for optional non-Latin ML Kit recognizers.
- Windows cross-drive Kotlin incremental-cache failures.
- Gemini JSON Schema payload compatibility and GHCR image-name generation.

## 0.2.0 - 2026-07-21

- Initial Flutter/FastAPI vertical slice with deterministic mock analysis.
