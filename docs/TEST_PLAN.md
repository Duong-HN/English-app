# Test plan

## Automated backend checks

- Ruff static checks.
- Known-vulnerability scan of production Python dependencies with pip-audit.
- Health and database readiness.
- Registration, duplicate email, login and invalid password.
- JWT profile access and password-hash non-disclosure.
- Authentication requirement on learning endpoints.
- Analysis persistence, deletion and user isolation.
- Learning-path generation, fixed seven-day schema, persistence, deletion and user isolation.
- Versioned Postman assets parse successfully, cover core routes and contain no committed credentials.
- Administrator authorization, statistics, user search and account lockout protections.
- Cross-user analysis moderation and administrator audit logging.
- Cross-user learning-path moderation and administrator audit logging.
- Teacher role promotion, teacher-only class creation and cross-teacher ownership isolation.
- Join-code rotation, pending membership approval, duplicate join conflicts, consent-preserving leave/rejoin and inactive classes.
- Assignment visibility, deadline/status updates, matching-analysis submission, multiple attempts and cross-class/private-analysis isolation.
- Active-class teacher role/deactivation guards and administrator audit entries for class, roster and assignment mutations.
- Clean Alembic migration through classroom revision `0004` on SQLite and PostgreSQL-compatible schema operations.
- Whitespace/input validation.
- Alembic upgrade from an empty database.
- Production Docker image build.

## Automated administrator web checks

- ESLint with React hook rules.
- Production vinext/Cloudflare Worker build and server-rendered login verification.
- API Console preset, custom-header validation, response-size and safe cURL tests.
- Learning-path dashboard and API Console presets.
- Teacher session gating, role-scoped navigation and classroom API contracts.
- Classroom creation, roster approval, assignment creation/lifecycle controls and submitted-analysis rendering states.
- Production Node dependency audit at high severity.
- Admin web Docker image build.

## Delivery checks

- GitHub Actions workflow validation with actionlint.
- Docker Compose startup with PostgreSQL, API and admin web health checks.
- Browser integration: admin login, dashboard metrics, readiness/stats requests, learner registration and mock AI analysis through API Console.
- Android release APK build with R8 enabled.

## Automated Flutter checks

- Dart formatting and `flutter analyze`.
- Login screen smoke test.
- API login payload and missing auth-header check.
- Bearer token propagation.
- Learning-path request payload and seven-day UI rendering.
- Classroom join, pending/active states, assignment lists and matching-analysis submission.
- OCR and speech-service adapters feeding editable study text through fakes.
- API validation-error parsing.
- Auth controller token persistence.
- Android debug build in CI.

## Manual device acceptance

Test on at least one physical Android device:

1. Register, close and reopen the app, verify session restoration.
2. Scan five clean and five difficult images; edit OCR output before submission.
3. Submit reading and writing samples; verify structured UI and history.
4. Dictate five English answers; verify transcript and clearly labeled limitations.
5. Generate a seven-day path after at least three analyses and verify its focus reflects recent activity.
6. Disable network during API calls and verify a readable error.
7. Delete a history item and verify it cannot be accessed again.
8. Join a classroom, verify pending approval, receive approval and open its assignments.
9. Submit a matching analysis to an assignment and verify the teacher can see it but cannot see unrelated history.

Record OCR accuracy, API latency, malformed AI responses, useful-feedback rate and cost across at least 20 representative samples.

## Commands

```powershell
.\scripts\check.ps1
.\scripts\release-check.ps1
```
