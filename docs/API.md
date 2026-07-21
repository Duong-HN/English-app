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

## Operations

- `GET /health` and `/health/live` — process liveness.
- `GET /health/ready` — database readiness.
- `GET /docs` — Swagger UI.
- `GET /openapi.json` — OpenAPI schema.

Validation errors use HTTP `422`, authentication failures `401`, ownership-safe missing resources `404`, conflicts `409`, and upstream AI failures `502`.
