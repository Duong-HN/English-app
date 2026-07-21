# Test plan

## Automated backend checks

- Ruff static checks.
- Known-vulnerability scan of production Python dependencies with pip-audit.
- Health and database readiness.
- Registration, duplicate email, login and invalid password.
- JWT profile access and password-hash non-disclosure.
- Authentication requirement on learning endpoints.
- Analysis persistence, deletion and user isolation.
- Whitespace/input validation.
- Alembic upgrade from an empty database.
- Production Docker image build.

## Delivery checks

- GitHub Actions workflow validation with actionlint.
- Docker Compose startup with PostgreSQL and API health checks.
- Android release APK build with R8 enabled.

## Automated Flutter checks

- Dart formatting and `flutter analyze`.
- Login screen smoke test.
- API login payload and missing auth-header check.
- Bearer token propagation.
- API validation-error parsing.
- Auth controller token persistence.
- Android debug build in CI.

## Manual device acceptance

Test on at least one physical Android device:

1. Register, close and reopen the app, verify session restoration.
2. Scan five clean and five difficult images; edit OCR output before submission.
3. Submit reading and writing samples; verify structured UI and history.
4. Dictate five English answers; verify transcript and clearly labeled limitations.
5. Disable network during API calls and verify a readable error.
6. Delete a history item and verify it cannot be accessed again.

Record OCR accuracy, API latency, malformed AI responses, useful-feedback rate and cost across at least 20 representative samples.

## Commands

```powershell
.\scripts\check.ps1
.\scripts\release-check.ps1
```
