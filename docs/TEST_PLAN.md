# Test plan

## Scope of evidence

This file is a test plan, not a claim that every listed check has already passed. The current automated tests support the
prototype workflows. PostgreSQL behavior, production deployment, public-scale load, external-provider quality and real-device
behavior require separate evidence.

The graduation submission must distinguish:

- automated tests that passed;
- manual checks that were executed;
- checks that remain planned;
- production controls that are outside the prototype scope.

## Academic AI evaluation

In addition to API and schema tests, evaluate at least 30–50 representative learner inputs. The sample should include correct
answers, grammar errors, vocabulary issues, short and long inputs, off-topic inputs, invalid inputs and multiple learner levels.

Each result should be assessed using a fixed rubric covering:

- correctness of detected issues;
- usefulness of the feedback;
- suitability for the learner level;
- reasonableness of the score;
- hallucination or unsupported claims;
- schema validity;
- latency and estimated provider cost.

Where possible, compare the AI result with a teacher or English-language expert and a simple baseline. Report the sample size,
rubric, results and known failure cases in the graduation report. AI output that merely conforms to a JSON schema is not proof
of educational quality.

## Automated backend checks

- Ruff static checks.
- Known-vulnerability scan of production Python dependencies with pip-audit.
- Health and database readiness.
- Registration, duplicate email, login and invalid password.
- JWT profile access and password-hash non-disclosure.
- Authentication requirement on learning endpoints.
- Analysis persistence, deletion and user isolation.
- Learning-path generation, fixed seven-day schema, persistence, deletion and user isolation.
- Onboarding resume states, 20-question answer completeness, skill scoring and idempotent path completion.
- Teacher/class ownership, invite-code joining, cross-class isolation, assignment resubmission and feedback authorization.
- Home aggregation of deadline-aware class work and the next personal task within the learner's daily budget.
- Versioned Postman assets parse successfully, cover core routes and contain no committed credentials.
- Administrator authorization, statistics, user search and account lockout protections.
- Cross-user analysis moderation and administrator audit logging.
- Cross-user learning-path moderation and administrator audit logging.
- Whitespace/input validation.
- Alembic upgrade from an empty database.
- Production Docker image build.

## Automated administrator web checks

- ESLint with React hook rules.
- Production vinext/Cloudflare Worker build and server-rendered login verification.
- API Console preset, custom-header validation, response-size and safe cURL tests.
- Learning-path dashboard and API Console presets.
- Teacher/admin role routing plus class, assignment and feedback API payload coverage.
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
- Goal/time onboarding, one-question placement navigation, result-to-path retry and server-state resume.
- Class joining, assignment listing/submission and combined Home dashboard rendering.
- OCR and speech-service adapters feeding editable study text through fakes.
- API validation-error parsing.
- Auth controller token persistence.
- Android debug build in CI.

## Manual device acceptance

Test on at least one physical Android device:

1. Register, close and reopen the app, verify session restoration.
2. Complete goal, daily-time and all 20 placement questions; verify Home opens with a generated route.
3. Stop onboarding at each step, reopen the app and verify it resumes from the server state.
4. Join a teacher-created class by invite code, submit an assignment and verify AI plus teacher feedback.
5. Scan five clean and five difficult images; edit OCR output before submission.
6. Submit reading and writing samples; verify structured UI and history.
7. Dictate five English answers; verify transcript and clearly labeled limitations.
8. Disable network during API calls and verify a readable error.
9. Delete a history item and verify it cannot be accessed again.

Record OCR accuracy, API latency, malformed AI responses, useful-feedback rate and cost across at least 20 representative samples.

## Commands

```powershell
.\scripts\check.ps1
.\scripts\release-check.ps1
```
