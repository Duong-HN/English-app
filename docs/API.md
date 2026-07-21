# API contract

Base path: `/api/v1`

## Authentication

- `POST /auth/register` — email, password and display name; returns JWT and user.
- `POST /auth/login` — email and password; returns JWT and user.
- `GET /auth/me` — current user; requires `Authorization: Bearer <token>`.

## Learning analysis

- `POST /analyses/reading`
- `POST /analyses/writing`
- `POST /analyses/speaking`
- `GET /analyses?limit=20&offset=0`
- `GET /analyses/{id}`
- `DELETE /analyses/{id}`

Analysis request:

```json
{
  "input_text": "The learner's English text"
}
```

Speaking input is a transcript. The API prompt explicitly excludes pronunciation claims.

## Personalized learning paths

- `POST /learning-paths/generate` — create and persist a seven-day path from the learner's goal, CEFR level, daily minutes and up to 20 recent analyses.
- `GET /learning-paths/current` — latest path owned by the authenticated learner.
- `GET /learning-paths?limit=20&offset=0` — learner-owned path history.
- `DELETE /learning-paths/{id}` — ownership-safe deletion.

Generate request:

```json
{
  "goal": "Communicate confidently at work",
  "current_level": "B1",
  "minutes_per_day": 30
}
```

The response contains exactly seven daily tasks with a skill, duration, activity and measurable success criterion. Supported levels are `A1`, `A2`, `B1`, `B2` and `C1`; daily time is limited to 10–120 minutes.

## Operations

- `GET /health` and `/health/live` — process liveness.
- `GET /health/ready` — database readiness.
- `GET /docs` — Swagger UI.
- `GET /openapi.json` — OpenAPI schema.

Validation errors use HTTP `422`, authentication failures `401`, ownership-safe missing resources `404`, conflicts `409`, and upstream AI failures `502`.

## Administration

All administration endpoints require a JWT belonging to an active user whose role is `admin`:

- `GET /admin/stats` — users, activity totals, analysis types and seven-day trend.
- `GET /admin/users?q=&role=&is_active=&limit=&offset=` — searchable user directory.
- `PATCH /admin/users/{id}` — activate/deactivate or promote/demote a user.
- `GET /admin/analyses?q=&type=&user_id=&limit=&offset=` — cross-user analysis review.
- `GET /admin/analyses/{id}` — complete analysis details.
- `DELETE /admin/analyses/{id}` — moderated deletion.
- `GET /admin/learning-paths?q=&user_id=&limit=&offset=` — cross-user learning-path review.
- `DELETE /admin/learning-paths/{id}` — moderated learning-path deletion.
- `GET /admin/audit-logs` — immutable administration activity history.

An administrator cannot deactivate or demote their own account, and the final active administrator cannot be disabled. User updates and analysis deletions create audit records without copying learner text into the audit payload.
