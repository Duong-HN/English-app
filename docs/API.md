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
  "input_text": "The learner's English text",
  "learning_path_id": "optional-path-id",
  "task_day": 3,
  "lesson_id": "optional-lesson-id"
}
```

When `lesson_id` is supplied from a self-study space, the API grounds the AI request with the course, level, unit,
lesson objective/body and published audio/video transcripts. The persisted analysis keeps `lesson_id` so feedback can
be traced back to the lesson. Class-space analyses cannot attach personal curriculum context.

Speaking input is currently a transcript. The API prompt explicitly excludes pronunciation claims; a real pronunciation
score requires a separately configured audio assessment provider and is not synthesized from transcript confidence.
When `learning_path_id` and `task_day` are supplied, the analysis is attached to that task and marks the day
complete after a successful analysis.

## Onboarding

New learner flow is resumable and server-owned:

- `GET /onboarding` — computed state for the active learning space, saved preferences, latest placement result and current learning path.
- `PATCH /onboarding/mode` — choose self-study with `{ "kind": "self" }` during first-run onboarding.
- `PATCH /onboarding/preferences` — save `goal` and/or `daily_minutes`.
- `POST /onboarding/complete` — idempotently generate the validated seven-day path after preferences and placement exist.

Goal codes are `ielts`, `communication`, `study_abroad` and `work`. Daily time choices are `15`, `20`, `30`,
`45` and `60`. Computed states also include `needs_mode` and `class_ready`; self-study states are
`needs_goal`, `needs_daily_time`, `needs_placement`, `needs_learning_path` and `completed`. Existing learners who
already own a learning path are safely backfilled and reported as completed.

### Learning spaces

- `GET /learning-spaces` — list the self-study space and every joined-class space.
- `POST /learning-spaces/self` — select self-study.
- `POST /learning-spaces/join` — join a class by invite code and create its isolated space.

Send `X-Learning-Space-ID` on learner requests to select a space. If omitted, the API uses the self-study space. A
class space has no personal placement/path or self-study curriculum; its home and progress are teacher-assignment
scoped. Analysis, vocabulary, placement, learning paths and lesson progress always include the active space in their
ownership filters.

```json
{
  "goal": "work",
  "daily_minutes": 30
}
```

## Placement test

- `GET /placement-test` — returns the public 20-question diagnostic without answer keys.
- `POST /placement-test/submit` — requires one `a`/`b`/`c`/`d` answer for every question, stores the attempt and
  updates the learner's level.
- `GET /placement-test/latest` — returns the latest diagnostic result.

The result is a starting-level estimate for LearnMate, not an official CEFR certificate. A learning path uses
the latest placement level when one exists; the existing `current_level` request field remains as a backwards-
compatible fallback for learners who have not completed the test.
Each public question identifies its `skill` (`grammar`, `vocabulary` or `reading`). Results include aggregate score,
CEFR starting level, per-skill correct/total/percentage values and `test_version`.

## Personalized learning paths

- `POST /learning-path-jobs` — enqueue a seven-day path generation job. The request returns `202` and a job id; clients poll the job until it succeeds or fails.
- `POST /learning-path-jobs/{learning_path_id}/adapt` — enqueue adaptation of an existing path from recent results and completed days.
- `GET /learning-path-jobs/{job_id}` — read an owned generation job and its resulting `learning_path_id`.
- `GET /learning-paths/{id}` — read an owned learning path by id after a generation job succeeds.
- `POST /learning-paths/generate` — legacy synchronous endpoint retained temporarily for compatibility; new clients must use `learning-path-jobs`.
- `GET /learning-paths/current` — latest path owned by the authenticated learner.
- `GET /learning-paths?limit=20&offset=0` — learner-owned path history.
- `PATCH /learning-paths/{id}/days/{day}` — mark a daily task complete/incomplete and optionally save a note.
- `POST /learning-paths/{id}/adapt` — compatibility alias for the asynchronous adaptation job; returns `202`.
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

Each path also returns `daily_progress`, `level_source` (`placement` or `self_reported`) and the associated
`placement_attempt_id` when available.

## Vocabulary

- `GET /vocabulary?status=new|learning|mastered` — list the learner's flashcards.
- `POST /vocabulary` — create or update a saved word.
- `POST /vocabulary/from-analysis/{analysis_id}` — idempotently save vocabulary extracted from a reading analysis.
- `GET /vocabulary/lookup/{word}` — fetch IPA/audio/meanings plus Datamuse synonyms, antonyms and full
  collocation phrases for an authenticated learner.
- `PATCH /vocabulary/{id}` — change review status or example.
- `DELETE /vocabulary/{id}` — remove a flashcard.

Reading analyses automatically upsert their extracted vocabulary, so words remain available outside the analysis
JSON result.
External word details use independent shared cache windows (30 days for Dictionary API and 7 days for Datamuse).
If a provider is temporarily unavailable, an expired validated entry is returned as a stale fallback; provider
failures do not overwrite it.

## Fixed curriculum

- `GET /content/courses?kind=core|ielts&level=A1|A2|B1|B2|C1` — list fixed courses and chapters.
- `GET /content/courses/{code}` — retrieve one course with lesson summaries and active-space progress.
- `GET /content/lessons/{id}` — retrieve lesson body, structured practice content, provenance, transcript, published media items and progress.
- `PATCH /content/lessons/{id}/progress` — set `started` or `completed` status, with optional score/note.
- `PATCH /content/lessons/{id}/media-progress` — save the current media position and completion state.
- `GET /content/media/{id}/stream` — authenticated stream for a private uploaded asset.

The catalog currently seeds one focused English A2→B1 content pack at `core-b1`, plus legacy core tracks for the other
levels and four IELTS band tracks from 4.5–5.5 through 7.0–8.0. The focused pack has six original lessons in two units;
its `content_pack` contains objectives, vocabulary, reading/listening prompts, practice items, answer keys and speaking/
writing tasks. Each lesson also returns `source_attribution` and `license_name`.
Each lesson can contain multiple `LessonMedia` rows. The API supports local multipart uploads and already-hosted
licensed URLs:

- `GET /content/admin/courses` — administrator-only catalog for media management.
- `GET /content/admin/lessons/{id}` — administrator-only lesson detail including draft media.
- `POST /content/admin/lessons/{id}/media` — administrator-only multipart upload with `file`, `media_type`, `title`,
  optional `duration_seconds`, `transcript`, `caption_url`, `sort_order` and `is_published` fields.
- `POST /content/admin/lessons/{id}/media/url` — administrator-only registration of an HTTPS audio/video URL.
- `DELETE /content/admin/media/{id}` — remove the database metadata and private uploaded file.

Uploaded files are stored outside the database under `MEDIA_STORAGE_DIR` and streamed only to authenticated users.
Docker mounts `/data/media` as the `learnmate_media` persistent volume. The repository does not ship copyrighted lesson
assets; an administrator must upload owned/licensed recordings or register a licensed CDN URL. `media_url` remains in
the response as a backwards-compatible alias for the first published media item.

## Teacher classes and assignments

Roles are separate: public registration creates `learner`; a learner can submit a teacher application; an
administrator must approve it before the account becomes `teacher`. Approved teachers retain access to the learner
endpoints and may use the same account as a learner; administrator access is not implied by the teacher role.

### Teacher applications

- `GET /teacher-applications/me` — learner reads their current application, or `{"application": null}` when none exists.
- `POST /teacher-applications` — learner-only endpoint for submitting a motivation and optional organization. A rejected application can be resubmitted; an approved teacher cannot submit a second application.
- `GET /admin/teacher-applications?status=pending|approved|rejected&limit=&offset=` — administrator reviews applications.
- `PATCH /admin/teacher-applications/{id}` — administrator approves or rejects a pending application and can add a review note.

Approval changes the applicant's role to `teacher`; rejection leaves the account as `learner`. Directly changing a
learner to `teacher` through `/admin/users/{id}` is rejected so every teacher account has a review record.

- `POST /classes` — teacher creates a class and receives its unique invite code.
- `GET /classes` — teacher-owned, learner-joined, or administrator-visible classes.
- `GET /classes/{id}` — class detail for the owner or a joined learner.
- `POST /classes/join` — learner joins idempotently with `{ "invite_code": "..." }`.
- `GET /classes/{id}/members` — private owner/administrator member list.
- `POST /classes/{id}/assignments` — owner (or administrator) creates an assignment.
- `GET /classes/{id}/assignments` — owner or joined learner list; learner items include submission state.
- `POST /assignments/{id}/submit` — joined learner submits/resubmits text for structured AI analysis.
- `GET /assignments/{id}/submission` — learner retrieves their own analysis and latest teacher feedback.
- `GET /assignments/{id}/submissions` — owner/administrator review queue.
- `PATCH /submissions/{id}/feedback` — owner/administrator saves teacher feedback.

```json
{
  "title": "Write a work email",
  "skill": "writing",
  "content": "Write a polite follow-up email.",
  "estimated_minutes": 15,
  "due_at": "2026-07-30T12:00:00Z"
}
```

Skills are limited to `reading`, `writing` and `speaking`; deadlines must be future timezone-aware timestamps and
late submission is rejected. Resubmission updates the same submission and analysis records, so retries do not create
duplicate work. AI output is nested under `analysis`; feedback is submitted as `{ "feedback": "..." }`.

## Learner home

- `GET /home` — returns the active self-study or class space.

Self-study responses include the personal path and next task. Class responses include only the selected class's
upcoming assignments and submission/feedback state; they do not expose or update the personal path.

## Operations

- `GET /health` and `/health/live` — process liveness.
- `GET /health/ready` — database readiness.
- `GET /docs` — Swagger UI.
- `GET /openapi.json` — OpenAPI schema.

Validation errors use HTTP `422`, authentication failures `401`, ownership-safe missing resources `404`, conflicts `409`, and upstream AI failures `502`.

## Administration

All administration endpoints require a JWT belonging to an active user whose role is `admin`:

- `GET /admin/stats` — users, activity totals, analysis types and seven-day trend.
- `GET /admin/users?q=&role=&is_active=&limit=&offset=` — searchable user directory; role accepts `learner`,
  `teacher` or `admin`.
- `PATCH /admin/users/{id}` — activate/deactivate or change administrative/learner access. Teacher access is granted through the teacher-application workflow.
- `GET /admin/teacher-applications?status=&limit=&offset=` — review learner teacher applications.
- `PATCH /admin/teacher-applications/{id}` — approve or reject a pending teacher application.
- `GET /admin/analyses?q=&type=&user_id=&limit=&offset=` — cross-user analysis review.
- `GET /admin/analyses/{id}` — complete analysis details.
- `DELETE /admin/analyses/{id}` — moderated deletion.
- `GET /admin/learning-paths?q=&user_id=&limit=&offset=` — cross-user learning-path review.
- `DELETE /admin/learning-paths/{id}` — moderated learning-path deletion.
- `GET /admin/audit-logs` — immutable administration activity history.

An administrator cannot deactivate or demote their own account, and the final active administrator cannot be disabled. User updates and analysis deletions create audit records without copying learner text into the audit payload.
