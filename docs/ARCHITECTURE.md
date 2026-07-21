# LearnMate AI — implementation blueprint

## Product boundary

The first release is a formative English-learning assistant, not an official IELTS scorer. The guaranteed MVP flow is:

```text
text input (camera OCR in phase 2) -> backend -> structured AI feedback -> saved history
```

Speaking is split into two claims:

1. Transcript evaluation: grammar, vocabulary and relevance.
2. Pronunciation practice: short recordings of selected target words. A pronunciation engine or phoneme-level analysis is required; STT alone is not a pronunciation score.

## Components

| Layer | Choice | Reason |
|---|---|---|
| Mobile | Flutter/Dart | One codebase for Android and iOS |
| API | FastAPI/Python | Typed request validation and easy automated tests |
| Local DB | SQLite | Zero setup for development and demo |
| Production DB | PostgreSQL | Same relational model, safe migration path |
| AI | Provider interface; Mock default, Gemini adapter optional | Tests and demos remain deterministic and cheap |
| OCR | On-device OCR adapter, added after text flow is stable | Camera/OCR does not block backend and UI work |
| Auth | Dev header now; Firebase Auth/OIDC before release | Do not ship the development identity mechanism |

## Database schema

### users

`id`, `email`, `display_name`, `role`, `level`, `created_at`

### analyses

`id`, `user_id`, `type`, `input_text`, `result` (JSON), `score`, `provider`, `created_at`

The JSON result is intentionally flexible for the MVP. Before production, add versioned result schemas and migrations for vocabulary, exercises and pronunciation attempts.

## API contract

- `GET /health`
- `POST /api/v1/analyses/reading`
- `POST /api/v1/analyses/writing`
- `POST /api/v1/analyses/speaking`
- `GET /api/v1/analyses?limit=20`

Request body:

```json
{"input_text":"The learner's English text"}
```

Every analysis is stored against the authenticated user. In development `X-Dev-User` is used only to make the vertical slice runnable. Production must replace it with verified Firebase/OIDC tokens, authorization rules, rate limiting and request logging with personal data redacted.

## 12-week delivery plan

1. Weeks 1–2: finalize scope, UI flows, API contract, database and test dataset.
2. Weeks 3–4: Flutter shell, API client, history and error states.
3. Weeks 5–6: Mock provider, then Gemini adapter; validate JSON and measure latency/cost.
4. Weeks 7–8: OCR camera adapter; always show/edit extracted text before analysis.
5. Week 9: writing and transcript-based speaking feedback.
6. Week 10: selected-word pronunciation experiment; report limitations honestly.
7. Weeks 11–12: integration tests, Android release build, user test, report and presentation build.

## Definition of done for the MVP

- A fresh checkout can run backend tests and Flutter tests.
- A learner can submit reading, writing and speaking text and see structured feedback.
- Results persist and appear in history.
- AI key is server-side only.
- Mock mode is deterministic; Gemini mode has timeout and error handling.
- At least 20 representative samples are evaluated manually and documented.
- Android APK is built from a tagged Git commit.
