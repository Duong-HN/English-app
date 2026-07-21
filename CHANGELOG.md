# Changelog

All notable changes to LearnMate AI are recorded here.

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
