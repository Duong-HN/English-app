from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (
    Assignment,
    AssignmentSubmission,
    LeaderboardSeason,
    Notification,
    PeerReviewAllocation,
    StudyGroupMember,
    User,
    utc_now,
)
from .push_service import dispatch_push

DEFAULT_RUBRIC = {
    "content": {"label": "Nội dung", "max_score": 5},
    "clarity": {"label": "Tính rõ ràng", "max_score": 5},
    "grammar": {"label": "Ngữ pháp", "max_score": 5},
    "vocabulary": {"label": "Từ vựng", "max_score": 5},
}

MAX_SEASON_SUBMISSION_POINTS = 100
MAX_SEASON_REVIEW_POINTS = 100


def normalized_rubric(value: dict | None) -> dict:
    if not value:
        return DEFAULT_RUBRIC.copy()
    result = {}
    for key, criterion in value.items():
        if not isinstance(key, str) or not isinstance(criterion, dict):
            continue
        label = str(criterion.get("label") or key).strip()[:120]
        max_score = float(criterion.get("max_score") or 5)
        if 0 < max_score <= 10:
            result[key[:40]] = {"label": label, "max_score": max_score}
    return result or DEFAULT_RUBRIC.copy()


def add_notification(
    db: Session,
    user_id: str,
    *,
    kind: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(notification)
    # Flush gives the notification its id before a push payload is built. The
    # delivery helper is best-effort and never raises into the user action.
    db.flush()
    dispatch_push(db, notification)
    return notification


def allocate_peer_reviews(
    db: Session,
    assignment: Assignment,
    submission: AssignmentSubmission,
) -> list[PeerReviewAllocation]:
    """Assign a balanced set of review tasks after a group submission."""

    if assignment.study_group_id is None:
        return []
    existing = set(
        db.scalars(
            select(PeerReviewAllocation.reviewer_id).where(
                PeerReviewAllocation.submission_id == submission.id,
            )
        ).all()
    )
    members = db.execute(
        select(StudyGroupMember, User)
        .join(User, User.id == StudyGroupMember.user_id)
        .where(
            StudyGroupMember.group_id == assignment.study_group_id,
            StudyGroupMember.status == "active",
            StudyGroupMember.user_id != submission.learner_id,
        )
        .order_by(StudyGroupMember.joined_at, StudyGroupMember.user_id)
    ).all()
    if not members:
        return []

    assignment_counts = dict(
        db.execute(
            select(PeerReviewAllocation.reviewer_id, func.count(PeerReviewAllocation.id))
            .join(AssignmentSubmission, AssignmentSubmission.id == PeerReviewAllocation.submission_id)
            .where(
                AssignmentSubmission.assignment_id == assignment.id,
                PeerReviewAllocation.reviewer_id != submission.learner_id,
            )
            .group_by(PeerReviewAllocation.reviewer_id)
        ).all()
    )
    ordered = sorted(
        members,
        key=lambda item: (assignment_counts.get(item[0].user_id, 0), item[0].joined_at, item[0].user_id),
    )
    slots = min(max(1, assignment.reviewers_per_submission), len(ordered))
    review_deadline = assignment.review_deadline or (assignment.due_at + timedelta(days=2))
    allocations: list[PeerReviewAllocation] = []
    for _membership, reviewer in ordered:
        if len(allocations) >= slots:
            break
        if reviewer.id in existing:
            continue
        allocation = PeerReviewAllocation(
            submission_id=submission.id,
            reviewer_id=reviewer.id,
            due_at=review_deadline,
        )
        db.add(allocation)
        allocations.append(allocation)
        add_notification(
            db,
            reviewer.id,
            kind="peer_review_assigned",
            title="Bạn có bài cần peer review",
            body="Một bài làm mới trong nhóm đang chờ bạn góp ý.",
            data={
                "group_id": assignment.study_group_id,
                "assignment_id": assignment.id,
                "submission_id": submission.id,
            },
        )
    return allocations


def current_leaderboard_season(db: Session, now: datetime | None = None) -> LeaderboardSeason:
    moment = now or utc_now()
    moment = moment.astimezone(UTC)
    start = datetime(moment.year, moment.month, moment.day, tzinfo=UTC) - timedelta(days=moment.weekday())
    end = start + timedelta(days=7)
    key = start.strftime("%G-W%V")
    season = db.scalar(select(LeaderboardSeason).where(LeaderboardSeason.season_key == key))
    if season is not None:
        return season
    season = LeaderboardSeason(
        season_key=key,
        label=f"Tuần {start.isocalendar().week}",
        starts_at=start,
        ends_at=end,
    )
    db.add(season)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        season = db.scalar(select(LeaderboardSeason).where(LeaderboardSeason.season_key == key))
        if season is None:
            raise
    return season
