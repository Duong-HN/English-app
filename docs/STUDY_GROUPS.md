# Study Groups

Study Group is the primary collaborative-learning domain in LearnMate. It is
separate from the legacy `Classroom` domain used by Teacher Dashboard.

## Product flow

```text
Create group -> share deep link/code -> join request -> owner approval
  -> create shared assignment -> submit work
  -> server assigns peer reviewers -> rubric review before deadline
  -> weekly leaderboard with capped points
```

Groups are small communities with a configurable limit of 4–8 members
(default 8). The invite URI has the form:

```text
learnmate://study-groups/join?token=<group-token>
```

The mobile app registers this custom scheme and opens a preview/approval flow.

## Main API

- `POST /api/v1/study-groups` — create a group.
- `GET /api/v1/study-groups` — list active memberships.
- `POST /api/v1/study-groups/join` — create a pending join request using `invite_code` or `invite_token`.
- `GET /api/v1/study-groups/invite-preview/{token}` — preview a deep-link invite.
- `GET /api/v1/study-groups/invitations` — list pending requests/invitations.
- `POST /api/v1/study-groups/invitations/{id}/approve` — owner approves a request.
- `POST /api/v1/study-groups/invitations/{id}/decline` — requester/owner declines.
- `POST /api/v1/study-groups/{id}/assignments` — any active member creates an assignment.
- `GET /api/v1/study-groups/{id}/assignments` — list group assignments.
- `GET /api/v1/study-groups/{id}/assignments/{assignment_id}/peer-reviews` — reviewer-specific queue.
- `POST /api/v1/submissions/{submission_id}/peer-reviews` — submit rubric review.
- `GET /api/v1/submissions/{submission_id}/peer-reviews` — author views received reviews.
- `GET /api/v1/leaderboards?level=B1` — weekly global leaderboard.
- `GET /api/v1/study-groups/{id}/leaderboard` — weekly group leaderboard.
- `GET /api/v1/notifications` — group activity and review notifications.

## Peer review rules

- Each group assignment has a rubric, review deadline and 1–2 reviewers per submission.
- The backend assigns reviewers with the lowest current allocation count and never assigns the author.
- A reviewer can submit one review per allocation; duplicate/self-review is rejected.
- All rubric criteria and scores are required. Feedback must contain at least 20 non-whitespace characters.
- Repetitive feedback is marked `flagged` and does not earn leaderboard points until quality review.
- Assignment and review deadlines are separate.

## Leaderboard rules

The season is the current UTC ISO week. Each completed group submission earns 10
points and each accepted peer review earns 5 points. Points are capped at 100
for submissions and 100 for reviews per season. Legacy Teacher-class work is
excluded from both global and group rankings.

The response includes `season_key`, `season_starts_at` and `season_ends_at` so
the client can show the active season. Average received review score is shown
as a quality metric but does not directly increase points.

## Domain boundaries

- `StudyGroup`, `StudyGroupMember`, `StudyGroupInvitation` and group assignments are the new primary domain.
- `Classroom`, `ClassMember` and class assignments remain for Teacher Dashboard compatibility.
- Legacy `/classes` endpoints filter out Study Groups.
- Teacher Dashboard remains an optional management/moderation surface; learner mobile is the primary product experience.
