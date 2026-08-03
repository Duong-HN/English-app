import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import (
    get_current_user,
    require_learner,
    require_teacher,
    require_teacher_or_admin,
)
from ..learning_spaces import ensure_class_space
from ..models import (
    Analysis,
    Assignment,
    AssignmentSubmission,
    ClassMember,
    Classroom,
    LearningSpace,
    User,
    utc_now,
)
from ..schemas import (
    AnalysisResponse,
    AssignmentCreateRequest,
    AssignmentGradingJobResponse,
    AssignmentListResponse,
    AssignmentResponse,
    AssignmentSubmissionListResponse,
    AssignmentSubmissionResponse,
    AssignmentSubmitRequest,
    ClassCreateRequest,
    ClassJoinRequest,
    ClassListResponse,
    ClassMemberListResponse,
    ClassMemberResponse,
    ClassResponse,
    SubmissionFeedbackUpdate,
)
from .assignment_jobs import enqueue_assignment_grading_job

router = APIRouter(tags=["classes and assignments"])
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


def _member_count(db: Session, class_id: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(ClassMember).where(ClassMember.class_id == class_id)) or 0
    )


def _class_response(
    db: Session,
    classroom: Classroom,
    teacher: User,
    viewer: User,
) -> ClassResponse:
    can_manage = viewer.role == "admin" or viewer.role == "teacher" and viewer.id == classroom.teacher_id
    learning_space = db.scalar(
        select(LearningSpace.id).where(
            LearningSpace.user_id == viewer.id,
            LearningSpace.kind == "class",
            LearningSpace.class_id == classroom.id,
        )
    )
    return ClassResponse(
        id=classroom.id,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.display_name,
        name=classroom.name,
        description=classroom.description,
        invite_code=classroom.invite_code if can_manage else None,
        member_count=_member_count(db, classroom.id),
        created_at=_as_utc(classroom.created_at),
        updated_at=_as_utc(classroom.updated_at) if classroom.updated_at else None,
        learning_space_id=learning_space,
    )


def _get_class(db: Session, class_id: str) -> Classroom:
    classroom = db.get(Classroom, class_id)
    if classroom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return classroom


def _require_class_owner(db: Session, class_id: str, user: User) -> Classroom:
    classroom = _get_class(db, class_id)
    if user.role != "admin" and not (user.role == "teacher" and classroom.teacher_id == user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Class owner access is required")
    return classroom


def _require_class_access(db: Session, classroom: Classroom, user: User) -> None:
    if user.role == "admin" or (user.role == "teacher" and classroom.teacher_id == user.id):
        return
    membership = db.scalar(
        select(ClassMember.id).where(
            ClassMember.class_id == classroom.id,
            ClassMember.learner_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")


def _assignment_response(
    assignment: Assignment,
    classroom: Classroom,
    submission: AssignmentSubmission | None = None,
) -> AssignmentResponse:
    return AssignmentResponse(
        id=assignment.id,
        class_id=assignment.class_id,
        class_name=classroom.name,
        created_by_id=assignment.created_by_id,
        title=assignment.title,
        skill=assignment.skill,
        content=assignment.content,
        estimated_minutes=assignment.estimated_minutes,
        due_at=_as_utc(assignment.due_at),
        created_at=_as_utc(assignment.created_at),
        updated_at=_as_utc(assignment.updated_at) if assignment.updated_at else None,
        submission_id=submission.id if submission else None,
        submission_status=submission.status if submission else None,
        teacher_feedback=submission.teacher_feedback if submission else None,
    )


def _submission_response(
    submission: AssignmentSubmission,
    learner: User,
    analysis: Analysis | None,
) -> AssignmentSubmissionResponse:
    return AssignmentSubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        learner_id=submission.learner_id,
        learner_name=learner.display_name,
        status=submission.status,
        input_text=submission.input_text,
        analysis=AnalysisResponse.model_validate(analysis) if analysis is not None else None,
        teacher_feedback=submission.teacher_feedback,
        submitted_at=_as_utc(submission.submitted_at),
        feedback_at=_as_utc(submission.feedback_at) if submission.feedback_at else None,
        updated_at=_as_utc(submission.updated_at) if submission.updated_at else None,
    )


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    request: ClassCreateRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    classroom = Classroom(
        teacher_id=teacher.id,
        name=request.name,
        description=request.description,
        invite_code=_new_invite_code(db),
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return _class_response(db, classroom, teacher, teacher)


@router.get("/classes", response_model=ClassListResponse)
def list_classes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = select(Classroom, User).join(User, User.id == Classroom.teacher_id)
    if user.role == "teacher":
        statement = (
            statement.outerjoin(ClassMember, ClassMember.class_id == Classroom.id)
            .where(or_(Classroom.teacher_id == user.id, ClassMember.learner_id == user.id))
            .distinct()
        )
    elif user.role == "learner":
        statement = statement.join(
            ClassMember,
            ClassMember.class_id == Classroom.id,
        ).where(ClassMember.learner_id == user.id)
    elif user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Class access is unavailable")
    rows = db.execute(statement.order_by(Classroom.created_at.desc())).all()
    return ClassListResponse(
        items=[_class_response(db, classroom, teacher, user) for classroom, teacher in rows],
        total=len(rows),
    )


@router.post("/classes/join", response_model=ClassResponse)
def join_class(
    request: ClassJoinRequest,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    classroom = db.scalar(select(Classroom).where(Classroom.invite_code == request.invite_code))
    if classroom is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite code is invalid")
    membership = db.scalar(
        select(ClassMember).where(
            ClassMember.class_id == classroom.id,
            ClassMember.learner_id == learner.id,
        )
    )
    if membership is None:
        db.add(ClassMember(class_id=classroom.id, learner_id=learner.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    ensure_class_space(db, learner, classroom)
    db.commit()
    teacher = db.get(User, classroom.teacher_id)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Class teacher is missing"
        )
    return _class_response(db, classroom, teacher, learner)


@router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class(
    class_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    classroom = _get_class(db, class_id)
    _require_class_access(db, classroom, user)
    teacher = db.get(User, classroom.teacher_id)
    if teacher is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Class teacher is missing"
        )
    return _class_response(db, classroom, teacher, user)


@router.get("/classes/{class_id}/members", response_model=ClassMemberListResponse)
def list_class_members(
    class_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_class_owner(db, class_id, user)
    rows = db.execute(
        select(ClassMember, User)
        .join(User, User.id == ClassMember.learner_id)
        .where(ClassMember.class_id == class_id)
        .order_by(ClassMember.joined_at)
    ).all()
    return ClassMemberListResponse(
        items=[
            ClassMemberResponse(
                id=membership.id,
                learner_id=learner.id,
                email=learner.email,
                display_name=learner.display_name,
                level=learner.level,
                joined_at=_as_utc(membership.joined_at),
            )
            for membership, learner in rows
        ],
        total=len(rows),
    )


@router.post(
    "/classes/{class_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    class_id: str,
    request: AssignmentCreateRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher_or_admin),
):
    classroom = _require_class_owner(db, class_id, teacher)
    assignment = Assignment(
        class_id=classroom.id,
        created_by_id=teacher.id,
        title=request.title,
        skill=request.skill,
        content=request.content,
        estimated_minutes=request.estimated_minutes,
        due_at=request.due_at.astimezone(UTC),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment, classroom)


@router.get("/classes/{class_id}/assignments", response_model=AssignmentListResponse)
def list_assignments(
    class_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    classroom = _get_class(db, class_id)
    _require_class_access(db, classroom, user)
    assignments = db.scalars(
        select(Assignment)
        .where(Assignment.class_id == class_id)
        .order_by(Assignment.due_at, Assignment.created_at)
    ).all()
    submissions: dict[str, AssignmentSubmission] = {}
    membership = None
    if user.role in {"learner", "teacher"}:
        membership = db.scalar(
            select(ClassMember.id).where(
                ClassMember.class_id == classroom.id,
                ClassMember.learner_id == user.id,
            )
        )
        if membership is not None:
            ensure_class_space(db, user, classroom)
    if membership is not None:
        submissions = {
            submission.assignment_id: submission
            for submission in db.scalars(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.learner_id == user.id,
                    AssignmentSubmission.assignment_id.in_([item.id for item in assignments]),
                )
            ).all()
        }
    return AssignmentListResponse(
        items=[_assignment_response(item, classroom, submissions.get(item.id)) for item in assignments],
        total=len(assignments),
    )


@router.post(
    "/assignments/{assignment_id}/submit",
    response_model=AssignmentGradingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_assignment(
    assignment_id: str,
    request: AssignmentSubmitRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    membership = db.scalar(
        select(ClassMember.id).where(
            ClassMember.class_id == assignment.class_id,
            ClassMember.learner_id == learner.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    classroom = db.get(Classroom, assignment.class_id)
    if classroom is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assignment class is missing",
        )
    if utc_now() > _as_utc(assignment.due_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assignment deadline has passed")
    return enqueue_assignment_grading_job(
        assignment=assignment,
        learner=learner,
        input_text=request.input_text,
        db=db,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/assignments/{assignment_id}/submission",
    response_model=AssignmentSubmissionResponse,
)
def get_own_submission(
    assignment_id: str,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    membership = db.scalar(
        select(ClassMember.id).where(
            ClassMember.class_id == assignment.class_id,
            ClassMember.learner_id == learner.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    ensure_class_space(db, learner, db.get(Classroom, assignment.class_id))
    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.learner_id == learner.id,
        )
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    analysis = db.get(Analysis, submission.analysis_id) if submission.analysis_id else None
    return _submission_response(submission, learner, analysis)


@router.get(
    "/assignments/{assignment_id}/submissions",
    response_model=AssignmentSubmissionListResponse,
)
def list_submissions(
    assignment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    _require_class_owner(db, assignment.class_id, user)
    rows = db.execute(
        select(AssignmentSubmission, User, Analysis)
        .join(User, User.id == AssignmentSubmission.learner_id)
        .outerjoin(Analysis, Analysis.id == AssignmentSubmission.analysis_id)
        .where(AssignmentSubmission.assignment_id == assignment.id)
        .order_by(AssignmentSubmission.submitted_at.desc())
    ).all()
    return AssignmentSubmissionListResponse(
        items=[_submission_response(submission, learner, analysis) for submission, learner, analysis in rows],
        total=len(rows),
    )


@router.patch("/submissions/{submission_id}/feedback", response_model=AssignmentSubmissionResponse)
def update_submission_feedback(
    submission_id: str,
    request: SubmissionFeedbackUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    submission = db.get(AssignmentSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    assignment = db.get(Assignment, submission.assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission assignment is missing"
        )
    _require_class_owner(db, assignment.class_id, user)
    submission.teacher_feedback = request.feedback
    submission.status = "reviewed"
    submission.feedback_at = utc_now()
    submission.updated_at = utc_now()
    db.commit()
    db.refresh(submission)
    learner = db.get(User, submission.learner_id)
    if learner is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission learner is missing"
        )
    analysis = db.get(Analysis, submission.analysis_id) if submission.analysis_id else None
    return _submission_response(submission, learner, analysis)
