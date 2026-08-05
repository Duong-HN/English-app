import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user, require_learner
from ..models import (
    Assignment,
    AssignmentSubmission,
    PeerReview,
    PeerReviewAllocation,
    StudyGroup,
    StudyGroupInvitation,
    StudyGroupMember,
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
    StudyGroupInvitationListResponse,
    StudyGroupInvitationResponse,
    StudyGroupInvitePreviewResponse,
    StudyGroupJoinRequest,
    StudyGroupJoinResponse,
    StudyGroupListResponse,
    StudyGroupMemberListResponse,
    StudyGroupMemberResponse,
    StudyGroupResponse,
)
from ..study_group_service import (
    MAX_SEASON_REVIEW_POINTS,
    MAX_SEASON_SUBMISSION_POINTS,
    add_notification,
    allocate_peer_reviews,
    current_leaderboard_season,
    normalized_rubric,
)

router = APIRouter(tags=["study groups"])
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_LINK_PREFIX = "learnmate://study-groups/join?token="


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _new_token(db: Session, model, field_name: str = "invite_token") -> str:
    for _ in range(20):
        token = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(12))
        column = getattr(model, field_name)
        if db.scalar(select(model.id).where(column == token)) is None:
            return token
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not allocate an invitation token",
    )


def _member_count(db: Session, group_id: str) -> int:
    return (
        db.scalar(
            select(func.count(StudyGroupMember.id)).where(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.status == "active",
            )
        )
        or 0
    )


def _get_group(db: Session, group_id: str) -> StudyGroup:
    group = db.get(StudyGroup, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study group not found")
    return group


def _get_group_by_invite(db: Session, request: StudyGroupJoinRequest) -> StudyGroup:
    if request.invite_token:
        group = db.scalar(select(StudyGroup).where(StudyGroup.invite_token == request.invite_token))
    else:
        group = db.scalar(select(StudyGroup).where(StudyGroup.invite_token == request.invite_code))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite link or code is invalid")
    return group


def _active_membership(db: Session, group_id: str, user_id: str) -> StudyGroupMember | None:
    return db.scalar(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id,
            StudyGroupMember.status == "active",
        )
    )


def _require_group_access(db: Session, group: StudyGroup, user: User) -> None:
    if user.role == "admin" or group.owner_id == user.id:
        return
    if _active_membership(db, group.id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study group not found")


def _require_group_owner(group: StudyGroup, user: User) -> None:
    if user.role != "admin" and group.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Group owner access is required")


def _group_response(db: Session, group: StudyGroup, viewer: User) -> StudyGroupResponse:
    owner = db.get(User, group.owner_id)
    pending = (
        db.scalar(
            select(func.count(StudyGroupInvitation.id)).where(
                StudyGroupInvitation.group_id == group.id,
                StudyGroupInvitation.status == "pending",
                StudyGroupInvitation.expires_at > utc_now(),
            )
        )
        or 0
    )
    return StudyGroupResponse(
        id=group.id,
        owner_id=group.owner_id,
        owner_name=owner.display_name if owner else "Learner",
        name=group.name,
        description=group.description,
        level=group.level,
        invite_code=group.invite_token if group.owner_id == viewer.id or viewer.role == "admin" else None,
        invite_link=(
            f"{INVITE_LINK_PREFIX}{group.invite_token}"
            if group.owner_id == viewer.id or _active_membership(db, group.id, viewer.id)
            else None
        ),
        member_limit=group.member_limit,
        member_count=_member_count(db, group.id),
        is_owner=group.owner_id == viewer.id,
        pending_invitation_count=pending if group.owner_id == viewer.id else 0,
        created_at=_as_utc(group.created_at),
        updated_at=_as_utc(group.updated_at) if group.updated_at else None,
    )


def _invitation_response(db: Session, invitation: StudyGroupInvitation) -> StudyGroupInvitationResponse:
    group = invitation.group or db.get(StudyGroup, invitation.group_id)
    inviter = invitation.inviter or db.get(User, invitation.inviter_id)
    invitee = invitation.invitee or db.get(User, invitation.invitee_id)
    return StudyGroupInvitationResponse(
        id=invitation.id,
        group_id=invitation.group_id,
        group_name=group.name if group else "Study group",
        inviter_id=invitation.inviter_id,
        inviter_name=inviter.display_name if inviter else "Learner",
        invitee_id=invitation.invitee_id,
        invitee_name=invitee.display_name if invitee else "Learner",
        kind=invitation.kind,
        status=invitation.status,
        token=invitation.token if invitation.status == "pending" else None,
        invite_link=(f"{INVITE_LINK_PREFIX}{group.invite_token}" if group else None),
        expires_at=_as_utc(invitation.expires_at),
        created_at=_as_utc(invitation.created_at),
        responded_at=_as_utc(invitation.responded_at) if invitation.responded_at else None,
    )


def _assignment_response(
    db: Session,
    assignment: Assignment,
    group: StudyGroup,
    viewer: User,
) -> StudyGroupAssignmentResponse:
    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.learner_id == viewer.id,
        )
    )
    creator = db.get(User, assignment.created_by_id)
    peer_review_count = (
        db.scalar(
            select(func.count(PeerReview.id))
            .join(AssignmentSubmission, AssignmentSubmission.id == PeerReview.submission_id)
            .where(
                AssignmentSubmission.assignment_id == assignment.id, PeerReview.quality_status == "accepted"
            )
        )
        or 0
    )
    review_deadline = assignment.review_deadline or assignment.due_at
    return StudyGroupAssignmentResponse(
        id=assignment.id,
        group_id=group.id,
        group_name=group.name,
        created_by_id=assignment.created_by_id,
        created_by_name=creator.display_name if creator else "Learner",
        title=assignment.title,
        skill=assignment.skill,
        content=assignment.content,
        estimated_minutes=assignment.estimated_minutes,
        due_at=_as_utc(assignment.due_at),
        review_deadline=_as_utc(review_deadline),
        reviewers_per_submission=assignment.reviewers_per_submission,
        rubric=normalized_rubric(assignment.rubric),
        created_at=_as_utc(assignment.created_at),
        updated_at=_as_utc(assignment.updated_at) if assignment.updated_at else None,
        submission_id=submission.id if submission else None,
        submission_status=submission.status if submission else None,
        peer_review_count=peer_review_count,
    )


def _get_group_assignment(db: Session, group_id: str, assignment_id: str) -> tuple[StudyGroup, Assignment]:
    group = _get_group(db, group_id)
    assignment = db.scalar(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.study_group_id == group.id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group assignment not found")
    return group, assignment


def _ensure_allocations(db: Session, assignment: Assignment) -> None:
    submissions = db.scalars(
        select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment.id)
    ).all()
    for submission in submissions:
        has_allocation = db.scalar(
            select(PeerReviewAllocation.id).where(PeerReviewAllocation.submission_id == submission.id)
        )
        if has_allocation is None:
            allocate_peer_reviews(db, assignment, submission)
    db.flush()


@router.post("/study-groups", response_model=StudyGroupResponse, status_code=status.HTTP_201_CREATED)
def create_study_group(
    request: StudyGroupCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    token = _new_token(db, StudyGroup)
    group = StudyGroup(
        owner_id=user.id,
        name=request.name,
        description=request.description,
        level=request.level,
        invite_token=token,
        member_limit=request.member_limit,
    )
    db.add(group)
    db.flush()
    db.add(StudyGroupMember(group_id=group.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(group)
    return _group_response(db, group, user)


@router.get("/study-groups", response_model=StudyGroupListResponse)
def list_study_groups(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(StudyGroup)
        .join(StudyGroupMember, StudyGroupMember.group_id == StudyGroup.id)
        .where(
            StudyGroupMember.user_id == user.id,
            StudyGroupMember.status == "active",
        )
        .order_by(StudyGroup.created_at.desc())
    ).all()
    return StudyGroupListResponse(
        items=[_group_response(db, group, user) for group in rows],
        total=len(rows),
    )


@router.post("/study-groups/join", response_model=StudyGroupJoinResponse)
def join_study_group(
    request: StudyGroupJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    group = _get_group_by_invite(db, request)
    if _active_membership(db, group.id, user.id) is not None:
        return StudyGroupJoinResponse(status="already_member", group=_group_response(db, group, user))
    if _member_count(db, group.id) >= group.member_limit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Study group is full")
    existing = db.scalar(
        select(StudyGroupInvitation).where(
            StudyGroupInvitation.group_id == group.id,
            StudyGroupInvitation.invitee_id == user.id,
            StudyGroupInvitation.status == "pending",
            StudyGroupInvitation.expires_at > utc_now(),
        )
    )
    if existing is None:
        existing = StudyGroupInvitation(
            group_id=group.id,
            inviter_id=group.owner_id,
            invitee_id=user.id,
            token=_new_token(db, StudyGroupInvitation, "token"),
            kind="join_request",
            expires_at=utc_now() + timedelta(days=7),
        )
        db.add(existing)
        add_notification(
            db,
            group.owner_id,
            kind="study_group_join_request",
            title="Có yêu cầu tham gia nhóm",
            body=f"{user.display_name} muốn tham gia nhóm {group.name}.",
            data={"group_id": group.id, "invitation_id": existing.id},
        )
        db.commit()
        db.refresh(existing)
    return StudyGroupJoinResponse(
        status="pending",
        group=_group_response(db, group, user),
        invitation=_invitation_response(db, existing),
    )


@router.get("/study-groups/invite-preview/{token}", response_model=StudyGroupInvitePreviewResponse)
def preview_study_group_invite(
    token: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = db.scalar(select(StudyGroup).where(StudyGroup.invite_token == token.upper()))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite link is invalid")
    return StudyGroupInvitePreviewResponse(
        group_id=group.id,
        group_name=group.name,
        description=group.description,
        level=group.level,
        member_count=_member_count(db, group.id),
        member_limit=group.member_limit,
        expires_at=None,
    )


@router.get("/study-groups/invitations", response_model=StudyGroupInvitationListResponse)
def list_study_group_invitations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(StudyGroupInvitation)
        .join(StudyGroup, StudyGroup.id == StudyGroupInvitation.group_id)
        .where(
            StudyGroupInvitation.status == "pending",
            StudyGroupInvitation.expires_at > utc_now(),
            (StudyGroupInvitation.invitee_id == user.id) | (StudyGroup.owner_id == user.id),
        )
        .order_by(StudyGroupInvitation.created_at.desc())
    ).all()
    return StudyGroupInvitationListResponse(
        items=[_invitation_response(db, item) for item in rows],
        total=len(rows),
    )


@router.post("/study-groups/invitations/{invitation_id}/approve", response_model=StudyGroupResponse)
def approve_study_group_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    invitation = db.get(StudyGroupInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    group = _get_group(db, invitation.group_id)
    _require_group_owner(group, user)
    if invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation is no longer pending")
    if _as_utc(invitation.expires_at) <= utc_now():
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation has expired")
    if _member_count(db, group.id) >= group.member_limit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Study group is full")
    if _active_membership(db, group.id, invitation.invitee_id) is None:
        db.add(StudyGroupMember(group_id=group.id, user_id=invitation.invitee_id, role="member"))
    invitation.status = "accepted"
    invitation.responded_at = utc_now()
    add_notification(
        db,
        invitation.invitee_id,
        kind="study_group_join_approved",
        title="Bạn đã được vào nhóm",
        body=f"Yêu cầu tham gia {group.name} đã được chấp nhận.",
        data={"group_id": group.id},
    )
    db.commit()
    return _group_response(db, group, user)


@router.post("/study-groups/invitations/{invitation_id}/decline", response_model=StudyGroupInvitationResponse)
def decline_study_group_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    invitation = db.get(StudyGroupInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    group = _get_group(db, invitation.group_id)
    if user.id not in {group.owner_id, invitation.invitee_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation access is required")
    if invitation.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation is no longer pending")
    invitation.status = "declined"
    invitation.responded_at = utc_now()
    db.commit()
    db.refresh(invitation)
    return _invitation_response(db, invitation)


@router.get("/study-groups/{group_id}", response_model=StudyGroupResponse)
def get_study_group(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    return _group_response(db, group, user)


@router.get("/study-groups/{group_id}/members", response_model=StudyGroupMemberListResponse)
def list_study_group_members(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    rows = db.execute(
        select(StudyGroupMember, User)
        .join(User, User.id == StudyGroupMember.user_id)
        .where(
            StudyGroupMember.group_id == group.id,
            StudyGroupMember.status == "active",
        )
        .order_by(StudyGroupMember.joined_at)
    ).all()
    return StudyGroupMemberListResponse(
        items=[
            StudyGroupMemberResponse(
                id=membership.id,
                user_id=member.id,
                email=member.email,
                display_name=member.display_name,
                level=member.level,
                is_owner=member.id == group.owner_id,
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
    review_deadline = request.review_deadline or (request.due_at + timedelta(days=2))
    if _as_utc(review_deadline) < _as_utc(request.due_at):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Review deadline must be after assignment deadline",
        )
    assignment = Assignment(
        class_id=None,
        study_group_id=group.id,
        created_by_id=user.id,
        title=request.title,
        skill=request.skill,
        content=request.content,
        estimated_minutes=request.estimated_minutes,
        due_at=request.due_at,
        review_deadline=review_deadline,
        reviewers_per_submission=request.reviewers_per_submission,
        rubric=normalized_rubric(request.rubric),
    )
    db.add(assignment)
    db.flush()
    for member in db.scalars(
        select(StudyGroupMember).where(
            StudyGroupMember.group_id == group.id,
            StudyGroupMember.status == "active",
            StudyGroupMember.user_id != user.id,
        )
    ).all():
        add_notification(
            db,
            member.user_id,
            kind="study_group_assignment_created",
            title="Nhóm có bài tập mới",
            body=f"{user.display_name} đã tạo bài {assignment.title} trong {group.name}.",
            data={"group_id": group.id, "assignment_id": assignment.id},
        )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(db, assignment, group, user)


@router.get("/study-groups/{group_id}/assignments", response_model=StudyGroupAssignmentListResponse)
def list_study_group_assignments(
    group_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.study_group_id == group.id)
        .order_by(Assignment.due_at, Assignment.created_at)
    ).all()
    return StudyGroupAssignmentListResponse(
        items=[_assignment_response(db, item, group, user) for item in assignments],
        total=len(assignments),
    )


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
    group, assignment = _get_group_assignment(db, group_id, assignment_id)
    _require_group_access(db, group, user)
    _ensure_allocations(db, assignment)
    rows = db.execute(
        select(PeerReviewAllocation, AssignmentSubmission, User)
        .join(AssignmentSubmission, AssignmentSubmission.id == PeerReviewAllocation.submission_id)
        .join(User, User.id == AssignmentSubmission.learner_id)
        .where(
            PeerReviewAllocation.reviewer_id == user.id,
            PeerReviewAllocation.status == "pending",
            AssignmentSubmission.assignment_id == assignment.id,
        )
        .order_by(PeerReviewAllocation.due_at, PeerReviewAllocation.created_at)
    ).all()
    rubric = normalized_rubric(assignment.rubric)
    review_deadline = assignment.review_deadline or assignment.due_at
    return PeerReviewQueueResponse(
        items=[
            PeerReviewTargetResponse(
                submission_id=submission.id,
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                author_id=submission.learner_id,
                author_name=author.display_name,
                input_text=submission.input_text,
                analysis=AnalysisResponse.model_validate(submission.analysis)
                if submission.analysis is not None
                else None,
                submitted_at=_as_utc(submission.submitted_at),
                allocation_id=allocation.id,
                review_deadline=_as_utc(allocation.due_at or review_deadline),
                rubric=rubric,
            )
            for allocation, submission, author in rows
        ],
        total=len(rows),
    )


def _validate_rubric_scores(assignment: Assignment, request: PeerReviewCreateRequest) -> tuple[dict, float]:
    rubric = normalized_rubric(assignment.rubric)
    if not request.rubric_scores:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rubric scores are required for this assignment",
        )
    if set(request.rubric_scores) != set(rubric):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Every rubric criterion must be scored exactly once",
        )
    weighted_total = 0.0
    for key, criterion in rubric.items():
        value = request.rubric_scores[key]
        max_score = float(criterion.get("max_score") or 5)
        if value < 0 or value > max_score:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Rubric score for {key} must be between 0 and {max_score:g}",
            )
        weighted_total += value / max_score * 10
    return request.rubric_scores, round(weighted_total / len(rubric), 2)


def _peer_review_response(db: Session, review: PeerReview) -> PeerReviewResponse:
    reviewer = db.get(User, review.reviewer_id)
    assignment = review.submission.assignment
    return PeerReviewResponse(
        id=review.id,
        submission_id=review.submission_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.display_name if reviewer else "Learner",
        allocation_id=review.allocation_id,
        score=review.score,
        feedback=review.feedback,
        rubric_scores=review.rubric_scores or {},
        quality_status=review.quality_status,
        review_deadline=(
            _as_utc(review.allocation.due_at)
            if review.allocation is not None
            else (_as_utc(assignment.review_deadline) if assignment and assignment.review_deadline else None)
        ),
        created_at=_as_utc(review.created_at),
        updated_at=_as_utc(review.updated_at) if review.updated_at else None,
    )


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
    submission = db.get(AssignmentSubmission, submission_id)
    if submission is None or submission.assignment.study_group_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    group = _get_group(db, submission.assignment.study_group_id)
    _require_group_access(db, group, user)
    if submission.learner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot review your own work")
    allocation = db.scalar(
        select(PeerReviewAllocation).where(
            PeerReviewAllocation.submission_id == submission.id,
            PeerReviewAllocation.reviewer_id == user.id,
        )
    )
    if allocation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This submission was not assigned to you",
        )
    if allocation.status == "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Peer review is already submitted")
    if _as_utc(allocation.due_at) <= utc_now():
        allocation.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Peer review deadline has passed")
    rubric_scores, score = _validate_rubric_scores(submission.assignment, request)
    quality_status = "accepted"
    flagged_reason = None
    words = request.feedback.casefold().split()
    if len(words) >= 8 and len(set(words)) / len(words) < 0.45:
        quality_status = "flagged"
        flagged_reason = "Feedback appears repetitive and needs a quality check"
    review = PeerReview(
        submission_id=submission.id,
        reviewer_id=user.id,
        allocation_id=allocation.id,
        score=score,
        feedback=request.feedback,
        rubric_scores=rubric_scores,
        quality_status=quality_status,
        flagged_reason=flagged_reason,
    )
    db.add(review)
    allocation.status = "completed"
    allocation.completed_at = utc_now()
    add_notification(
        db,
        submission.learner_id,
        kind="peer_review_received",
        title="Bạn đã nhận được peer review",
        body="Một thành viên đã gửi góp ý cho bài làm của bạn.",
        data={
            "group_id": group.id,
            "submission_id": submission.id,
            "assignment_id": submission.assignment_id,
        },
    )
    db.commit()
    db.refresh(review)
    return _peer_review_response(db, review)


@router.get("/submissions/{submission_id}/peer-reviews", response_model=list[PeerReviewResponse])
def list_peer_reviews(
    submission_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_learner),
):
    submission = db.get(AssignmentSubmission, submission_id)
    if submission is None or submission.assignment.study_group_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if submission.learner_id != user.id:
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
    season = current_leaderboard_season(db)
    member_ids: set[str] | None = None
    if group_id is not None:
        member_ids = set(
            db.scalars(
                select(StudyGroupMember.user_id).where(
                    StudyGroupMember.group_id == group_id,
                    StudyGroupMember.status == "active",
                )
            ).all()
        )
    user_query = select(User).where(User.is_active.is_(True))
    if level is not None:
        user_query = user_query.where(User.level == level)
    if member_ids is not None:
        if not member_ids:
            return LeaderboardResponse(
                level=level,
                season_key=season.season_key,
                season_label=season.label,
                season_starts_at=_as_utc(season.starts_at),
                season_ends_at=_as_utc(season.ends_at),
                items=[],
                total=0,
            )
        user_query = user_query.where(User.id.in_(member_ids))
    users = db.scalars(user_query).all()
    user_ids = [user.id for user in users]
    if not user_ids:
        return LeaderboardResponse(
            level=level,
            season_key=season.season_key,
            season_label=season.label,
            season_starts_at=_as_utc(season.starts_at),
            season_ends_at=_as_utc(season.ends_at),
            items=[],
            total=0,
        )

    submission_query = (
        select(AssignmentSubmission.learner_id, func.count(AssignmentSubmission.id))
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(
            Assignment.study_group_id.is_not(None),
            AssignmentSubmission.learner_id.in_(user_ids),
            AssignmentSubmission.submitted_at >= season.starts_at,
            AssignmentSubmission.submitted_at < season.ends_at,
        )
        .group_by(AssignmentSubmission.learner_id)
    )
    if group_id is not None:
        submission_query = submission_query.where(Assignment.study_group_id == group_id)
    submission_counts = dict(db.execute(submission_query).all())

    given_query = (
        select(PeerReview.reviewer_id, func.count(PeerReview.id))
        .join(PeerReviewAllocation, PeerReviewAllocation.id == PeerReview.allocation_id)
        .join(AssignmentSubmission, AssignmentSubmission.id == PeerReview.submission_id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(
            Assignment.study_group_id.is_not(None),
            PeerReview.reviewer_id.in_(user_ids),
            PeerReview.quality_status == "accepted",
            PeerReview.created_at >= season.starts_at,
            PeerReview.created_at < season.ends_at,
        )
        .group_by(PeerReview.reviewer_id)
    )
    if group_id is not None:
        given_query = given_query.where(Assignment.study_group_id == group_id)
    given_counts = dict(db.execute(given_query).all())

    received_query = (
        select(AssignmentSubmission.learner_id, func.avg(PeerReview.score))
        .join(PeerReview, PeerReview.submission_id == AssignmentSubmission.id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .where(
            Assignment.study_group_id.is_not(None),
            AssignmentSubmission.learner_id.in_(user_ids),
            PeerReview.quality_status == "accepted",
            PeerReview.created_at >= season.starts_at,
            PeerReview.created_at < season.ends_at,
        )
        .group_by(AssignmentSubmission.learner_id)
    )
    if group_id is not None:
        received_query = received_query.where(Assignment.study_group_id == group_id)
    received_scores = dict(db.execute(received_query).all())

    ranked = sorted(
        users,
        key=lambda item: (
            -(
                min(submission_counts.get(item.id, 0) * 10, MAX_SEASON_SUBMISSION_POINTS)
                + min(given_counts.get(item.id, 0) * 5, MAX_SEASON_REVIEW_POINTS)
            ),
            item.display_name.casefold(),
        ),
    )
    items = []
    previous_points = None
    previous_rank = 0
    for index, item in enumerate(ranked, start=1):
        submissions_count = int(submission_counts.get(item.id, 0))
        reviews_count = int(given_counts.get(item.id, 0))
        points = min(submissions_count * 10, MAX_SEASON_SUBMISSION_POINTS) + min(
            reviews_count * 5,
            MAX_SEASON_REVIEW_POINTS,
        )
        rank = previous_rank if previous_points == points else index
        previous_points = points
        previous_rank = rank
        items.append(
            LeaderboardEntryResponse(
                rank=rank,
                user_id=item.id,
                display_name=item.display_name,
                level=item.level,
                points=points,
                submissions_count=submissions_count,
                peer_reviews_count=reviews_count,
                average_review_score=(
                    round(float(received_scores[item.id]), 2)
                    if received_scores.get(item.id) is not None
                    else None
                ),
            )
        )
    return LeaderboardResponse(
        level=level,
        season_key=season.season_key,
        season_label=season.label,
        season_starts_at=_as_utc(season.starts_at),
        season_ends_at=_as_utc(season.ends_at),
        items=items,
        total=len(items),
    )


@router.get("/leaderboards", response_model=LeaderboardResponse)
def global_leaderboard(
    level: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _leaderboard(db, level)


@router.get("/study-groups/{group_id}/leaderboard", response_model=LeaderboardResponse)
def study_group_leaderboard(
    group_id: str,
    level: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    group = _get_group(db, group_id)
    _require_group_access(db, group, user)
    return _leaderboard(db, level, group_id=group.id)
