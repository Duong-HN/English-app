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

Validation errors use HTTP `422`, authentication failures `401`, insufficient-role failures `403`, ownership-safe missing resources `404`, conflicts `409`, and upstream AI failures `502`.

## Classrooms and assignments

Public registration still creates only `learner` users. Administrators can
promote an account to `teacher`. Teacher authorization is server-side and every
class operation additionally checks `classes.teacher_id`; an ordinary teacher
cannot manage another teacher's class.

Teacher-only creation:

- `POST /classes` — teacher creates an owned class and receives a shareable join code.

Teacher-owner or administrator management routes:

- `GET /classes/managed?limit=&offset=` — teacher-owned classes; administrators receive all classes.
- `PATCH /classes/{id}` — owner/admin class update.
- `POST /classes/{id}/join-code/rotate` — invalidate the previous code and issue a new one.
- `GET /classes/{id}/members?limit=&offset=` — owner/admin roster.
- `PATCH /classes/{id}/members/{membership_id}` — approve with `active` or remove with `removed`.
- `POST /classes/{id}/assignments` — create a `published` or `closed` reading, writing or speaking assignment; `due_at`, when present, must include a timezone.
- `PATCH /assignments/{id}` — update assignment content/deadline or switch between `published` and `closed`; `skill_type` is immutable after creation.
- `GET /assignments/{id}/submissions?limit=&offset=` — owner/admin view of explicitly submitted work.

Shared authorized detail routes:

- `GET /classes/{id}` — owner/admin, or a learner with a pending/active membership; learner responses never include the join code.
- `GET /assignments/{id}` — owner/admin, or an active learner while the class is active.

Learner routes:

- `POST /classes/join` with `{ "join_code": "..." }` — request membership in `pending` state.
- `GET /classes/mine?limit=&offset=` — own pending and active memberships; join codes are never returned.
- `DELETE /classes/{id}/membership` — leave the class.
- `GET /classes/{id}/assignments?limit=&offset=` — all published and closed assignments for an active member while the class is active.
- `POST /assignments/{id}/submissions` with `{ "analysis_id": "..." }` — submit an owned, type-compatible analysis only while the assignment is `published`, not overdue and the class is active.

A learner may join multiple classes. Duplicate pending/active joins return
`409`. Invalid or inactive join codes use a safe `404`. Submitting another
learner's analysis, reading another class, or managing a class without ownership
is denied by the API. Closed, overdue and inactive-class submissions return
`409` or an ownership-safe `404` as appropriate. Once an analysis has been submitted as class work it
cannot be deleted while the submission references it. A removed learner must
submit the join code again and return to `pending`; a manager cannot reactivate
that membership without a new learner request.

## Administration

All `/admin` endpoints require a JWT belonging to an active user whose role is `admin`:

- `GET /admin/stats` — users, activity totals, analysis types and seven-day trend.
- `GET /admin/users?q=&role=&is_active=&limit=&offset=` — searchable user directory.
- `PATCH /admin/users/{id}` — activate/deactivate or change a user among `learner`, `teacher` and `admin`.
- `GET /admin/analyses?q=&type=&user_id=&limit=&offset=` — cross-user analysis review.
- `GET /admin/analyses/{id}` — complete analysis details.
- `DELETE /admin/analyses/{id}` — moderated deletion.
- `GET /admin/learning-paths?q=&user_id=&limit=&offset=` — cross-user learning-path review.
- `DELETE /admin/learning-paths/{id}` — moderated learning-path deletion.
- `GET /admin/audit-logs` — immutable administration activity history.

An administrator cannot deactivate or demote their own account, and the final active administrator cannot be disabled. A teacher with active classes cannot be disabled or moved to another role until those classes are paused; a paused class cannot be reopened unless its owner is again an active teacher. Administrator user moderation, class/roster/assignment mutations and analysis deletions create audit records without copying learner text into the audit payload.
