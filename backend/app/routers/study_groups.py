import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user, require_learner
from ..learning_spaces import ensure_class_space
from ..models import (
    Analysis,
    Assignment,
    AssignmentSubmission,
    ClassMember,
    Classroom,
    PeerReview,
    User,
    utc_now,
)
from ..schemas import (
    AnalysisResponse,
    AssignmentCreateRequest,
    LeaderboardEntryResponse,
    LeaderboardResponse,
    PeerReviewCreateRequest,
    PeerReviewQueueResponse,
    PeerReviewResponse,
    PeerReviewTargetResponse,
    StudyGroupAssignmentListResponse,
    StudyGroupAssignmentResponse,
    StudyGroupCreateRequest,
    StudyGroupJoinRequest,
    StudyGroupListResponse,
    StudyGroupMemberListResponse,
    StudyGroupMemberResponse,
    StudyGroupResponse,
)

router = APIRouter(tags=["study groups"])
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _new_invite_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
        if db.scalar(select(Classroom.id).where(Classroom.invite_code == code)) is None:
            return code
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate an invite code",
    )


def _get_group(db: Session, group_id: str) -> Classroom:
    group = db.scalar(
        select(Classroom).where(
            Classroom.id == group_id,
            Classroom.is_study_group.is_(True),
        )
    )
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study group not found")
    return group


def _is_group_member(db: Session, group: Classroom, user: User) -> bool:
    if group.teacher_id == user.id or user.role == "admin":
        return True
    return (
        db.scalar(
            select(ClassMember.id).where(
                ClassMember.class_id == group.id,
                ClassMember.learner_id == user.id,
            )
        )
        is not None
    )


def _require_group_access(db: Session, group: Classroom, user: User) -> None:
    if not _is_group_member(db, group, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study group not found")


def _group_response(db: Session, group: Classroom, viewer: User) -> StudyGroupResponse:
    owner = db.get(User, group.teacher_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Study group owner is missing",
        )
    count = (
        db.scalar(select(func.count()).select_from(ClassMember).where(ClassMember.class_id == group.id)) or 0
    )
    is_owner = viewer.role == "admin" or group.teacher_id == viewer.id
    return StudyGroupResponse(
        id=group.id,
        owner_id=owner.id,
        owner_name=owner.display_name,
        name=group.name,
        description=group.description,
        level=group.level,
        invite_code=group.invite_code if is_owner else None,
        member_count=count,
        is_owner=is_owner,
        created_at=_as_utc(group.created_at),
        updated_at=_as_utc(group.updated_at) if group.updated_at else None,
    )


def _assignment_response(
    db: Session,
    assignment: Assignment,
    group: Classroom,
    submission: AssignmentSubmission | None = None,
) -> StudyGroupAssignmentResponse:
    creator = db.get(User, assignment.created_by_id)
    if creator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assignment creator is missing",
        )
    review_count = (
        db.scalar(
            select(func.count())
            .select_from(PeerReview)
            .join(AssignmentSubmission, AssignmentSubmission.id == PeerReview.submission_id)
            .where(AssignmentSubmission.assignment_id == assignment.id)
        )
        or 0
    )
    return StudyGroupAssignmentResponse(
        id=assignment.id,
        group_id=assignment.class_id,
        group_name=group.name,
        created_by_id=assignment.created_by_id,
        created_by_name=creator.display_name,
        title=assignment.title,
        skill=assignment.skill,
        content=assignment.content,
        estimated_minutes=assignment.estimated_minutes,
        due_at=_as_utc(assignment.due_at),
        created_at=_as_utc(assignment.created_at),
        updated_at=_as_utc(assignment.updated_at) if assignment.updated_at else None,
        submission_id=submission.id if submission else None,
        submission_status=submission.status if submission else None,
        peer_review_count=review_count,
    )


def _peer_review_response(db: Session, review: PeerReview) -> PeerReviewResponse:
    reviewer = db.get(User, review.reviewer_id)
    if reviewer is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Peer reviewer is missing",
        )
    return PeerReviewResponse(
        id=review.id,
        submission_id=review.submission_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.display_name,
        score=float(review.score),
        feedback=review.feedback,
        created_at=_as_utc(review.created_at),
        updated_at=_as_utc(review.updated_at) if review.updated_at else None,
    )


@router.post(
    "/study-groups",
    response_model=StudyGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_study_group(
    request: StudyGroupCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    group = Classroom(
        teacher_id=user.id,
        name=request.name,
        description=request.description,
        level=request.level,
        is_study_group=True,
        invite_code=_new_invite_code(db),
    )
    db.add(group)
    db.flush()
    db.add(ClassMember(class_id=group.id, learner_id=user.id))
    db.commit()
    db.refresh(group)
    return _group_response(db, group, user)


@router.get("/study-groups", response_model=StudyGroupListResponse)
def list_study_groups(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = (
        select(Classroom)
        .outerjoin(ClassMember, ClassMember.class_id == Classroom.id)
        .where(
            Classroom.is_study_group.is_(True),
            or_(Classroom.teacher_id == user.id, ClassMember.learner_id == user.id),
        )
        .distinct()
        .order_by(Classroom.created_at.desc())
    )
    groups = db.scalars(statement).all()
    return StudyGroupListResponse(
        items=[_group_response(db, group, user) for group in groups],
        total=len(groups),
    )


@router.post("/study-groups/join", response_model=StudyGroupResponse)
def join_study_group(
    request: StudyGroupJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    group = db.scalar(
        select(Classroom).where(
            Classroom.invite_code == request.invite_code,
            Classroom.is_study_group.is_(True),
        )
    )
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code is invalid")
    membership = db.scalar(
        select(ClassMember).where(
            ClassMember.class_id == group.id,
            ClassMember.learner_id == user.id,
        )
    )
    if membership is None:
        db.add(ClassMember(class_id=group.id, learner_id=user.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    ensure_class_space(db, user, group)
    db.commit()
    return _group_response(db, group, user)


@router.get("/study-groups/{group_id}", response_model=StudyGroupResponse)
def get_study_group(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    return _group_response(db, group, user)


@router.get(
    "/study-groups/{group_id}/members",
    response_model=StudyGroupMemberListResponse,
)
def list_study_group_members(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    rows = db.execute(
        select(ClassMember, User)
        .join(User, User.id == ClassMember.learner_id)
        .where(ClassMember.class_id == group.id)
        .order_by(ClassMember.joined_at)
    ).all()
    return StudyGroupMemberListResponse(
        items=[
            StudyGroupMemberResponse(
                id=membership.id,
                user_id=member.id,
                email=member.email,
                display_name=member.display_name,
                level=member.level,
                is_owner=member.id == group.teacher_id,
                joined_at=_as_utc(membership.joined_at),
            )
            for membership, member in rows
        ],
        total=len(rows),
    )


@router.post(
    "/study-groups/{group_id}/assignments",
    response_model=StudyGroupAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_study_group_assignment(
    group_id: str,
    request: AssignmentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    assignment = Assignment(
        class_id=group.id,
        created_by_id=user.id,
        title=request.title,
        skill=request.skill,
        content=request.content,
        estimated_minutes=request.estimated_minutes,
        due_at=request.due_at.astimezone(UTC),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _assignment_response(db, assignment, group)


@router.get(
    "/study-groups/{group_id}/assignments",
    response_model=StudyGroupAssignmentListResponse,
)
def list_study_group_assignments(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.class_id == group.id)
        .order_by(Assignment.due_at, Assignment.created_at)
    ).all()
    submissions = (
        {
            submission.assignment_id: submission
            for submission in db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id.in_([item.id for item in assignments]),
                    AssignmentSubmission.learner_id == user.id,
                )
            ).all()
        }
        if assignments
        else {}
    )
    return StudyGroupAssignmentListResponse(
        items=[_assignment_response(db, item, group, submissions.get(item.id)) for item in assignments],
        total=len(assignments),
    )


def _submission_group(
    db: Session,
    submission_id: str,
    user: User,
) -> tuple[AssignmentSubmission, Assignment, Classroom]:
    submission = db.get(AssignmentSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    assignment = db.get(Assignment, submission.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    group = _get_group(db, assignment.class_id)
    _require_group_access(db, group, user)
    return submission, assignment, group


@router.get(
    "/study-groups/{group_id}/assignments/{assignment_id}/peer-reviews",
    response_model=PeerReviewQueueResponse,
)
def peer_review_queue(
    group_id: str,
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    assignment = db.get(Assignment, assignment_id)
    if assignment is None or assignment.class_id != group.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    submissions = db.scalars(
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.learner_id != user.id,
        )
        .order_by(AssignmentSubmission.submitted_at)
    ).all()
    targets: list[PeerReviewTargetResponse] = []
    for submission in submissions:
        already_reviewed = db.scalar(
            select(PeerReview.id).where(
                PeerReview.submission_id == submission.id,
                PeerReview.reviewer_id == user.id,
            )
        )
        if already_reviewed is not None:
            continue
        author = db.get(User, submission.learner_id)
        if author is None:
            continue
        analysis = db.get(Analysis, submission.analysis_id) if submission.analysis_id else None
        targets.append(
            PeerReviewTargetResponse(
                submission_id=submission.id,
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                author_id=author.id,
                author_name=author.display_name,
                input_text=submission.input_text,
                analysis=AnalysisResponse.model_validate(analysis) if analysis else None,
                submitted_at=_as_utc(submission.submitted_at),
            )
        )
    return PeerReviewQueueResponse(items=targets, total=len(targets))


@router.post(
    "/submissions/{submission_id}/peer-reviews",
    response_model=PeerReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_peer_review(
    submission_id: str,
    request: PeerReviewCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    submission, _, _ = _submission_group(db, submission_id, user)
    if submission.learner_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot review your own submission",
        )
    review = db.scalar(
        select(PeerReview).where(
            PeerReview.submission_id == submission.id,
            PeerReview.reviewer_id == user.id,
        )
    )
    now = utc_now()
    if review is None:
        review = PeerReview(
            submission_id=submission.id,
            reviewer_id=user.id,
            score=request.score,
            feedback=request.feedback,
            created_at=now,
        )
        db.add(review)
    else:
        review.score = request.score
        review.feedback = request.feedback
        review.updated_at = now
    if submission.status == "submitted":
        submission.status = "peer_reviewed"
        submission.updated_at = now
    db.commit()
    db.refresh(review)
    return _peer_review_response(db, review)


@router.get(
    "/submissions/{submission_id}/peer-reviews",
    response_model=list[PeerReviewResponse],
)
def list_peer_reviews(
    submission_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    submission, _, _ = _submission_group(db, submission_id, user)
    if submission.learner_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author can view peer reviews",
        )
    reviews = db.scalars(
        select(PeerReview).where(PeerReview.submission_id == submission.id).order_by(PeerReview.created_at)
    ).all()
    return [_peer_review_response(db, review) for review in reviews]


def _leaderboard(
    db: Session,
    level: str | None,
    group_id: str | None = None,
) -> LeaderboardResponse:
    member_ids: set[str] | None = None
    if group_id is not None:
        member_ids = set(
            db.scalars(select(ClassMember.learner_id).where(ClassMember.class_id == group_id)).all()
        )
    user_query = select(User).where(User.is_active.is_(True))
    if level is not None:
        user_query = user_query.where(User.level == level)
    if member_ids is not None:
        if not member_ids:
            return LeaderboardResponse(level=level, items=[], total=0)
        user_query = user_query.where(User.id.in_(member_ids))
    users = db.scalars(user_query).all()
    if not users:
        return LeaderboardResponse(level=level, items=[], total=0)
    user_ids = [user.id for user in users]
    study_group_class_ids = select(Classroom.id).where(Classroom.is_study_group.is_(True))

    submission_query = (
        select(AssignmentSubmission.learner_id, func.count(AssignmentSubmission.id))
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(AssignmentSubmission.learner_id.in_(user_ids))
        .group_by(AssignmentSubmission.learner_id)
    )
    if group_id is not None:
        submission_query = submission_query.where(Assignment.class_id == group_id)
    else:
        submission_query = submission_query.where(Assignment.class_id.in_(study_group_class_ids))
    submission_counts = dict(db.execute(submission_query).all())

    given_query = (
        select(PeerReview.reviewer_id, func.count(PeerReview.id))
        .join(AssignmentSubmission, AssignmentSubmission.id == PeerReview.submission_id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(PeerReview.reviewer_id.in_(user_ids))
        .group_by(PeerReview.reviewer_id)
    )
    if group_id is not None:
        given_query = given_query.where(Assignment.class_id == group_id)
    else:
        given_query = given_query.where(Assignment.class_id.in_(study_group_class_ids))
    given_counts = dict(db.execute(given_query).all())

    received_query = (
        select(AssignmentSubmission.learner_id, func.avg(PeerReview.score))
        .join(PeerReview, PeerReview.submission_id == AssignmentSubmission.id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(AssignmentSubmission.learner_id.in_(user_ids))
        .group_by(AssignmentSubmission.learner_id)
    )
    if group_id is not None:
        received_query = received_query.where(Assignment.class_id == group_id)
    else:
        received_query = received_query.where(Assignment.class_id.in_(study_group_class_ids))
    received_scores = dict(db.execute(received_query).all())

    ranked = sorted(
        users,
        key=lambda item: (
            -((submission_counts.get(item.id, 0) * 10) + (given_counts.get(item.id, 0) * 5)),
            -submission_counts.get(item.id, 0),
            -given_counts.get(item.id, 0),
            item.display_name.casefold(),
        ),
    )
    entries = [
        LeaderboardEntryResponse(
            rank=index,
            user_id=user.id,
            display_name=user.display_name,
            level=user.level,
            points=(submission_counts.get(user.id, 0) * 10) + (given_counts.get(user.id, 0) * 5),
            submissions_count=submission_counts.get(user.id, 0),
            peer_reviews_count=given_counts.get(user.id, 0),
            average_review_score=(
                round(float(received_scores[user.id]), 2) if user.id in received_scores else None
            ),
        )
        for index, user in enumerate(ranked, start=1)
    ]
    return LeaderboardResponse(level=level, items=entries, total=len(entries))


@router.get("/leaderboards", response_model=LeaderboardResponse)
def global_leaderboard(
    level: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _leaderboard(db, level)


@router.get(
    "/study-groups/{group_id}/leaderboard",
    response_model=LeaderboardResponse,
)
def study_group_leaderboard(
    group_id: str,
    level: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    return _leaderboard(db, level, group_id=group.id)
