import secrets
import string
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user, require_learner, require_teacher
from ..models import (
    AdminAuditLog,
    Analysis,
    AssignmentSubmission,
    ClassAssignment,
    ClassMembership,
    Classroom,
    User,
    utc_now,
)
from ..schemas import (
    AnalysisResponse,
    AssignmentSubmissionCreate,
    AssignmentSubmissionListResponse,
    AssignmentSubmissionResponse,
    ClassAssignmentCreate,
    ClassAssignmentListResponse,
    ClassAssignmentResponse,
    ClassAssignmentUpdate,
    ClassroomCreate,
    ClassroomJoinCodeResponse,
    ClassroomJoinRequest,
    ClassroomMemberListResponse,
    ClassroomMemberResponse,
    ClassroomMemberUpdate,
    ClassroomUpdate,
    LearnerClassroomListResponse,
    LearnerClassroomResponse,
    ManagedClassroomListResponse,
    ManagedClassroomResponse,
    MessageResponse,
)

router = APIRouter(tags=["classes"])

_JOIN_CODE_ALPHABET = string.ascii_uppercase + string.digits
_VISIBLE_MEMBERSHIP_STATUSES = ("pending", "active")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_or_none(value: datetime | None) -> datetime | None:
    return _as_utc(value) if value is not None else None


def _record_admin_audit(
    db: Session,
    user: User,
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: dict,
) -> None:
    if user.role != "admin":
        return
    db.add(
        AdminAuditLog(
            admin_user_id=user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


def _new_join_code(db: Session) -> str:
    for _ in range(10):
        candidate = "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(10))
        if db.scalar(select(Classroom.id).where(Classroom.join_code == candidate)) is None:
            return candidate
    raise RuntimeError("Could not generate a unique class join code")


def _class_row(db: Session, class_id: str):
    return db.execute(
        select(Classroom, User).join(User, User.id == Classroom.teacher_id).where(Classroom.id == class_id)
    ).one_or_none()


def _managed_class_row(db: Session, class_id: str, user: User):
    row = _class_row(db, class_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    classroom, _ = row
    if user.role != "admin" and not (user.role == "teacher" and classroom.teacher_id == user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return row


def _membership(
    db: Session,
    class_id: str,
    learner_id: str,
    statuses: tuple[str, ...] | None = None,
) -> ClassMembership | None:
    query = select(ClassMembership).where(
        ClassMembership.class_id == class_id,
        ClassMembership.learner_id == learner_id,
    )
    if statuses:
        query = query.where(ClassMembership.status.in_(statuses))
    return db.scalar(query)


def _class_counts(db: Session, class_id: str) -> tuple[int, int, int]:
    active_members = (
        db.scalar(
            select(func.count())
            .select_from(ClassMembership)
            .where(
                ClassMembership.class_id == class_id,
                ClassMembership.status == "active",
            )
        )
        or 0
    )
    pending_members = (
        db.scalar(
            select(func.count())
            .select_from(ClassMembership)
            .where(
                ClassMembership.class_id == class_id,
                ClassMembership.status == "pending",
            )
        )
        or 0
    )
    assignments = (
        db.scalar(
            select(func.count()).select_from(ClassAssignment).where(ClassAssignment.class_id == class_id)
        )
        or 0
    )
    return int(active_members), int(pending_members), int(assignments)


def _managed_response(
    classroom: Classroom,
    teacher: User,
    active_member_count: int,
    pending_member_count: int,
    assignment_count: int,
) -> ManagedClassroomResponse:
    return ManagedClassroomResponse(
        id=classroom.id,
        teacher_id=teacher.id,
        teacher_email=teacher.email,
        teacher_display_name=teacher.display_name,
        name=classroom.name,
        description=classroom.description,
        target_level=classroom.target_level,
        join_code=classroom.join_code,
        is_active=classroom.is_active,
        active_member_count=active_member_count,
        pending_member_count=pending_member_count,
        assignment_count=assignment_count,
        created_at=_as_utc(classroom.created_at),
        updated_at=_utc_or_none(classroom.updated_at),
    )


def _managed_response_from_db(
    db: Session,
    classroom: Classroom,
    teacher: User,
) -> ManagedClassroomResponse:
    return _managed_response(classroom, teacher, *_class_counts(db, classroom.id))


def _learner_response(
    classroom: Classroom,
    teacher: User,
    membership: ClassMembership,
) -> LearnerClassroomResponse:
    return LearnerClassroomResponse(
        id=classroom.id,
        teacher_id=teacher.id,
        teacher_email=teacher.email,
        teacher_display_name=teacher.display_name,
        name=classroom.name,
        description=classroom.description,
        target_level=classroom.target_level,
        is_active=classroom.is_active,
        membership_id=membership.id,
        membership_status=membership.status,
        joined_at=_as_utc(membership.joined_at),
        approved_at=_utc_or_none(membership.approved_at),
        created_at=_as_utc(classroom.created_at),
        updated_at=_utc_or_none(classroom.updated_at),
    )


def _member_response(membership: ClassMembership, learner: User) -> ClassroomMemberResponse:
    return ClassroomMemberResponse(
        id=membership.id,
        class_id=membership.class_id,
        learner_id=learner.id,
        learner_email=learner.email,
        learner_display_name=learner.display_name,
        learner_level=learner.level,
        learner_is_active=learner.is_active,
        status=membership.status,
        joined_at=_as_utc(membership.joined_at),
        approved_at=_utc_or_none(membership.approved_at),
        updated_at=_utc_or_none(membership.updated_at),
    )


def _assignment_row(db: Session, assignment_id: str):
    return db.execute(
        select(ClassAssignment, Classroom, User)
        .join(Classroom, Classroom.id == ClassAssignment.class_id)
        .join(User, User.id == ClassAssignment.created_by)
        .where(ClassAssignment.id == assignment_id)
    ).one_or_none()


def _assignment_access(db: Session, assignment_id: str, user: User, *, manager_only: bool = False):
    row = _assignment_row(db, assignment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment, classroom, _ = row
    is_manager = user.role == "admin" or (user.role == "teacher" and classroom.teacher_id == user.id)
    if is_manager:
        return row
    if not manager_only and user.role == "learner" and classroom.is_active:
        membership = _membership(db, classroom.id, user.id, ("active",))
        if membership is not None:
            return row
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")


def _assignment_counts(db: Session, assignment_id: str, user_id: str) -> tuple[int, int]:
    total = (
        db.scalar(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(AssignmentSubmission.assignment_id == assignment_id)
        )
        or 0
    )
    mine = (
        db.scalar(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.learner_id == user_id,
            )
        )
        or 0
    )
    return int(total), int(mine)


def _assignment_response(
    assignment: ClassAssignment,
    classroom: Classroom,
    creator: User,
    submission_count: int,
    my_submission_count: int,
) -> ClassAssignmentResponse:
    return ClassAssignmentResponse(
        id=assignment.id,
        class_id=classroom.id,
        class_name=classroom.name,
        created_by_id=creator.id,
        created_by_display_name=creator.display_name,
        title=assignment.title,
        instructions=assignment.instructions,
        skill_type=assignment.skill_type,
        target_level=assignment.target_level,
        due_at=_utc_or_none(assignment.due_at),
        status=assignment.status,
        submission_count=submission_count,
        my_submission_count=my_submission_count,
        created_at=_as_utc(assignment.created_at),
        updated_at=_utc_or_none(assignment.updated_at),
    )


def _submission_response(
    submission: AssignmentSubmission,
    learner: User,
    analysis: Analysis,
) -> AssignmentSubmissionResponse:
    return AssignmentSubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        learner_id=learner.id,
        learner_email=learner.email,
        learner_display_name=learner.display_name,
        analysis_id=analysis.id,
        attempt_number=submission.attempt_number,
        status=submission.status,
        submitted_at=_as_utc(submission.submitted_at),
        analysis=AnalysisResponse.model_validate(analysis),
    )


@router.post(
    "/classes",
    response_model=ManagedClassroomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_classroom(
    request: ClassroomCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    locked_teacher = db.scalar(select(User).where(User.id == teacher.id).with_for_update())
    if locked_teacher is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access is required",
        )
    db.refresh(locked_teacher)
    if locked_teacher.role != "teacher" or not locked_teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access is required",
        )
    teacher = locked_teacher
    classroom = Classroom(
        teacher_id=teacher.id,
        name=request.name,
        description=request.description,
        target_level=request.target_level,
        join_code=_new_join_code(db),
    )
    db.add(classroom)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not allocate a unique class join code",
        ) from exc
    db.refresh(classroom)
    return _managed_response(classroom, teacher, 0, 0, 0)


@router.get("/classes/managed", response_model=ManagedClassroomListResponse)
def managed_classrooms(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in {"teacher", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Class management access is required"
        )

    filters = [] if user.role == "admin" else [Classroom.teacher_id == user.id]
    total = db.scalar(select(func.count()).select_from(Classroom).where(*filters)) or 0
    active_count = (
        select(func.count())
        .select_from(ClassMembership)
        .where(
            ClassMembership.class_id == Classroom.id,
            ClassMembership.status == "active",
        )
        .correlate(Classroom)
        .scalar_subquery()
    )
    pending_count = (
        select(func.count())
        .select_from(ClassMembership)
        .where(
            ClassMembership.class_id == Classroom.id,
            ClassMembership.status == "pending",
        )
        .correlate(Classroom)
        .scalar_subquery()
    )
    assignment_count = (
        select(func.count())
        .select_from(ClassAssignment)
        .where(ClassAssignment.class_id == Classroom.id)
        .correlate(Classroom)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Classroom, User, active_count, pending_count, assignment_count)
        .join(User, User.id == Classroom.teacher_id)
        .where(*filters)
        .order_by(Classroom.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ManagedClassroomListResponse(
        items=[
            _managed_response(classroom, teacher, int(active), int(pending), int(assignments))
            for classroom, teacher, active, pending, assignments in rows
        ],
        total=total,
    )


@router.get("/classes/mine", response_model=LearnerClassroomListResponse)
def learner_classrooms(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    filters = (
        ClassMembership.learner_id == learner.id,
        ClassMembership.status.in_(_VISIBLE_MEMBERSHIP_STATUSES),
    )
    total = db.scalar(select(func.count()).select_from(ClassMembership).where(*filters)) or 0
    rows = db.execute(
        select(Classroom, User, ClassMembership)
        .join(ClassMembership, ClassMembership.class_id == Classroom.id)
        .join(User, User.id == Classroom.teacher_id)
        .where(*filters)
        .order_by(ClassMembership.joined_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return LearnerClassroomListResponse(
        items=[_learner_response(classroom, teacher, membership) for classroom, teacher, membership in rows],
        total=total,
    )


@router.post(
    "/classes/join",
    response_model=LearnerClassroomResponse,
    status_code=status.HTTP_201_CREATED,
)
def join_classroom(
    request: ClassroomJoinRequest,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    row = db.execute(
        select(Classroom, User)
        .join(User, User.id == Classroom.teacher_id)
        .where(
            Classroom.join_code == request.join_code,
            Classroom.is_active.is_(True),
        )
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    classroom, teacher = row
    membership = db.scalar(
        select(ClassMembership)
        .where(
            ClassMembership.class_id == classroom.id,
            ClassMembership.learner_id == learner.id,
        )
        .with_for_update()
    )
    if membership is not None and membership.status in _VISIBLE_MEMBERSHIP_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending or active membership already exists",
        )

    now = utc_now()
    if membership is None:
        membership = ClassMembership(
            class_id=classroom.id,
            learner_id=learner.id,
            status="pending",
            joined_at=now,
        )
        db.add(membership)
    else:
        membership.status = "pending"
        membership.joined_at = now
        membership.approved_at = None
        membership.updated_at = now
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A membership already exists",
        ) from exc
    db.refresh(membership)
    return _learner_response(classroom, teacher, membership)


@router.get(
    "/classes/{class_id}",
    response_model=ManagedClassroomResponse | LearnerClassroomResponse,
)
def get_classroom(
    class_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = _class_row(db, class_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    classroom, teacher = row
    if user.role == "admin" or (user.role == "teacher" and classroom.teacher_id == user.id):
        return _managed_response_from_db(db, classroom, teacher)
    if user.role == "learner":
        membership = _membership(db, class_id, user.id, _VISIBLE_MEMBERSHIP_STATUSES)
        if membership is not None:
            return _learner_response(classroom, teacher, membership)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")


@router.patch("/classes/{class_id}", response_model=ManagedClassroomResponse)
def update_classroom(
    class_id: str,
    update: ClassroomUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    classroom, teacher = _managed_class_row(db, class_id, user)
    if update.is_active is True and not classroom.is_active:
        locked_teacher = db.scalar(select(User).where(User.id == teacher.id).with_for_update())
        if locked_teacher is not None:
            db.refresh(locked_teacher)
        if locked_teacher is None or locked_teacher.role != "teacher" or not locked_teacher.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A class requires an active teacher before it can be reopened",
            )
        teacher = locked_teacher
    changed = False
    changed_fields: list[str] = []
    for field in ("name", "description", "target_level", "is_active"):
        if field in update.model_fields_set:
            value = getattr(update, field)
            if getattr(classroom, field) != value:
                setattr(classroom, field, value)
                changed = True
                changed_fields.append(field)
    if changed:
        classroom.updated_at = utc_now()
        _record_admin_audit(
            db,
            user,
            action="class.updated",
            target_type="class",
            target_id=classroom.id,
            details={"changed_fields": changed_fields},
        )
        db.commit()
        db.refresh(classroom)
    return _managed_response_from_db(db, classroom, teacher)


@router.post("/classes/{class_id}/join-code/rotate", response_model=ClassroomJoinCodeResponse)
def rotate_join_code(
    class_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    classroom, _ = _managed_class_row(db, class_id, user)
    classroom.join_code = _new_join_code(db)
    classroom.updated_at = utc_now()
    _record_admin_audit(
        db,
        user,
        action="class.join_code_rotated",
        target_type="class",
        target_id=classroom.id,
        details={},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not allocate a unique class join code",
        ) from exc
    db.refresh(classroom)
    return ClassroomJoinCodeResponse(
        join_code=classroom.join_code,
        updated_at=_as_utc(classroom.updated_at),
    )


@router.get("/classes/{class_id}/members", response_model=ClassroomMemberListResponse)
def list_classroom_members(
    class_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _managed_class_row(db, class_id, user)
    total = (
        db.scalar(
            select(func.count()).select_from(ClassMembership).where(ClassMembership.class_id == class_id)
        )
        or 0
    )
    rows = db.execute(
        select(ClassMembership, User)
        .join(User, User.id == ClassMembership.learner_id)
        .where(ClassMembership.class_id == class_id)
        .order_by(ClassMembership.joined_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ClassroomMemberListResponse(
        items=[_member_response(membership, learner) for membership, learner in rows],
        total=total,
    )


@router.patch(
    "/classes/{class_id}/members/{membership_id}",
    response_model=ClassroomMemberResponse,
)
def update_classroom_member(
    class_id: str,
    membership_id: str,
    update: ClassroomMemberUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _managed_class_row(db, class_id, user)
    row = db.execute(
        select(ClassMembership, User)
        .join(User, User.id == ClassMembership.learner_id)
        .where(
            ClassMembership.id == membership_id,
            ClassMembership.class_id == class_id,
        )
        .with_for_update()
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    membership, learner = row
    previous_status = membership.status
    if previous_status == "removed" and update.status == "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The learner must request to join the class again",
        )
    now = utc_now()
    membership.status = update.status
    if update.status == "active" and membership.approved_at is None:
        membership.approved_at = now
    membership.updated_at = now
    _record_admin_audit(
        db,
        user,
        action="class.membership_updated",
        target_type="class_membership",
        target_id=membership.id,
        details={
            "class_id": class_id,
            "learner_id": learner.id,
            "from": previous_status,
            "to": update.status,
        },
    )
    db.commit()
    db.refresh(membership)
    return _member_response(membership, learner)


@router.delete("/classes/{class_id}/membership", response_model=MessageResponse)
def leave_classroom(
    class_id: str,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    membership = db.scalar(
        select(ClassMembership)
        .where(
            ClassMembership.class_id == class_id,
            ClassMembership.learner_id == learner.id,
            ClassMembership.status.in_(_VISIBLE_MEMBERSHIP_STATUSES),
        )
        .with_for_update()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    membership.status = "removed"
    membership.updated_at = utc_now()
    db.commit()
    return MessageResponse(message="Class membership removed")


def _class_assignment_access(db: Session, class_id: str, user: User):
    row = _class_row(db, class_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    classroom, _ = row
    if user.role == "admin" or (user.role == "teacher" and classroom.teacher_id == user.id):
        return row
    if (
        user.role == "learner"
        and classroom.is_active
        and _membership(db, class_id, user.id, ("active",)) is not None
    ):
        return row
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")


@router.get("/classes/{class_id}/assignments", response_model=ClassAssignmentListResponse)
def list_class_assignments(
    class_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _class_assignment_access(db, class_id, user)
    total = (
        db.scalar(
            select(func.count()).select_from(ClassAssignment).where(ClassAssignment.class_id == class_id)
        )
        or 0
    )
    submission_count = (
        select(func.count())
        .select_from(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == ClassAssignment.id)
        .correlate(ClassAssignment)
        .scalar_subquery()
    )
    my_submission_count = (
        select(func.count())
        .select_from(AssignmentSubmission)
        .where(
            AssignmentSubmission.assignment_id == ClassAssignment.id,
            AssignmentSubmission.learner_id == user.id,
        )
        .correlate(ClassAssignment)
        .scalar_subquery()
    )
    rows = db.execute(
        select(ClassAssignment, Classroom, User, submission_count, my_submission_count)
        .join(Classroom, Classroom.id == ClassAssignment.class_id)
        .join(User, User.id == ClassAssignment.created_by)
        .where(ClassAssignment.class_id == class_id)
        .order_by(ClassAssignment.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ClassAssignmentListResponse(
        items=[
            _assignment_response(assignment, classroom, creator, int(submissions), int(mine))
            for assignment, classroom, creator, submissions, mine in rows
        ],
        total=total,
    )


@router.post(
    "/classes/{class_id}/assignments",
    response_model=ClassAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_class_assignment(
    class_id: str,
    request: ClassAssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    classroom, _ = _managed_class_row(db, class_id, user)
    if not classroom.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The class must be active before assignments can be created",
        )
    assignment = ClassAssignment(
        class_id=classroom.id,
        created_by=user.id,
        title=request.title,
        instructions=request.instructions,
        skill_type=request.skill_type,
        target_level=request.target_level,
        due_at=request.due_at,
        status=request.status,
    )
    db.add(assignment)
    db.flush()
    _record_admin_audit(
        db,
        user,
        action="class_assignment.created",
        target_type="class_assignment",
        target_id=assignment.id,
        details={
            "class_id": classroom.id,
            "skill_type": request.skill_type,
            "target_level": request.target_level,
            "status": request.status,
        },
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment, classroom, user, 0, 0)


@router.get("/assignments/{assignment_id}", response_model=ClassAssignmentResponse)
def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment, classroom, creator = _assignment_access(db, assignment_id, user)
    return _assignment_response(
        assignment,
        classroom,
        creator,
        *_assignment_counts(db, assignment.id, user.id),
    )


@router.patch("/assignments/{assignment_id}", response_model=ClassAssignmentResponse)
def update_assignment(
    assignment_id: str,
    update: ClassAssignmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment, classroom, creator = _assignment_access(
        db,
        assignment_id,
        user,
        manager_only=True,
    )
    changed_fields: list[str] = []
    for field in ("title", "instructions", "target_level", "due_at", "status"):
        if field in update.model_fields_set:
            value = getattr(update, field)
            if getattr(assignment, field) != value:
                setattr(assignment, field, value)
                changed_fields.append(field)
    if changed_fields:
        assignment.updated_at = utc_now()
        _record_admin_audit(
            db,
            user,
            action="class_assignment.updated",
            target_type="class_assignment",
            target_id=assignment.id,
            details={
                "class_id": classroom.id,
                "changed_fields": changed_fields,
            },
        )
        db.commit()
        db.refresh(assignment)
    return _assignment_response(
        assignment,
        classroom,
        creator,
        *_assignment_counts(db, assignment.id, user.id),
    )


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionListResponse,
)
def list_assignment_submissions(
    assignment_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment, _, _ = _assignment_access(db, assignment_id, user, manager_only=True)
    total = (
        db.scalar(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(AssignmentSubmission.assignment_id == assignment.id)
        )
        or 0
    )
    rows = db.execute(
        select(AssignmentSubmission, User, Analysis)
        .join(User, User.id == AssignmentSubmission.learner_id)
        .join(Analysis, Analysis.id == AssignmentSubmission.analysis_id)
        .where(AssignmentSubmission.assignment_id == assignment.id)
        .order_by(AssignmentSubmission.submitted_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AssignmentSubmissionListResponse(
        items=[_submission_response(submission, learner, analysis) for submission, learner, analysis in rows],
        total=total,
    )


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_assignment(
    assignment_id: str,
    request: AssignmentSubmissionCreate,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    assignment, classroom, _ = _assignment_access(db, assignment_id, learner)
    db.execute(select(Classroom.id).where(Classroom.id == classroom.id).with_for_update()).scalar_one()
    db.execute(
        select(ClassAssignment.id).where(ClassAssignment.id == assignment.id).with_for_update()
    ).scalar_one()
    db.refresh(classroom)
    db.refresh(assignment)
    if not classroom.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if assignment.status != "published" or (
        assignment.due_at is not None and _as_utc(assignment.due_at) <= utc_now()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment is closed",
        )
    membership = db.scalar(
        select(ClassMembership)
        .where(
            ClassMembership.class_id == classroom.id,
            ClassMembership.learner_id == learner.id,
            ClassMembership.status == "active",
        )
        .with_for_update()
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == request.analysis_id,
            Analysis.user_id == learner.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    if analysis.type != assignment.skill_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis type does not match assignment skill type",
        )

    previous_attempt = (
        db.scalar(
            select(func.max(AssignmentSubmission.attempt_number)).where(
                AssignmentSubmission.assignment_id == assignment.id,
                AssignmentSubmission.learner_id == learner.id,
            )
        )
        or 0
    )
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        learner_id=learner.id,
        analysis_id=analysis.id,
        attempt_number=int(previous_attempt) + 1,
        status="submitted",
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A concurrent submission attempt conflicted",
        ) from exc
    db.refresh(submission)
    return _submission_response(submission, learner, analysis)
