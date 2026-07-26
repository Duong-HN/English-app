from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import require_learner
from ..models import (
    Assignment,
    AssignmentSubmission,
    ClassMember,
    Classroom,
    LearnerProfile,
    LearningPath,
    User,
    utc_now,
)
from ..schemas import (
    HomeClassAssignmentResponse,
    HomePersonalTaskResponse,
    HomeResponse,
    LearningPathResponse,
)

router = APIRouter(prefix="/home", tags=["learner home"])


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _latest_path(db: Session, user_id: str) -> LearningPath | None:
    return db.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user_id)
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )


def _next_personal_task(
    learning_path: LearningPath | None,
    available_minutes: int,
) -> HomePersonalTaskResponse | None:
    if learning_path is None or available_minutes <= 0:
        return None
    progress = learning_path.daily_progress or {}
    for raw_task in learning_path.plan.get("daily_tasks", []):
        if not isinstance(raw_task, dict):
            continue
        day = raw_task.get("day")
        if not isinstance(day, int):
            continue
        day_progress = progress.get(str(day), {})
        if isinstance(day_progress, dict) and day_progress.get("completed"):
            continue
        return HomePersonalTaskResponse(
            learning_path_id=learning_path.id,
            day=day,
            title=str(raw_task.get("title", "")),
            skill=str(raw_task.get("skill", "mixed")),
            activity=str(raw_task.get("activity", "")),
            duration_minutes=min(
                int(raw_task.get("duration_minutes", learning_path.minutes_per_day)),
                available_minutes,
            ),
            success_criteria=str(raw_task.get("success_criteria", "")),
        )
    return None


@router.get("", response_model=HomeResponse)
def learner_home(
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    profile = db.get(LearnerProfile, learner.id)
    learning_path = _latest_path(db, learner.id)
    rows = db.execute(
        select(Assignment, Classroom, AssignmentSubmission)
        .join(ClassMember, ClassMember.class_id == Assignment.class_id)
        .join(Classroom, Classroom.id == Assignment.class_id)
        .outerjoin(
            AssignmentSubmission,
            and_(
                AssignmentSubmission.assignment_id == Assignment.id,
                AssignmentSubmission.learner_id == learner.id,
            ),
        )
        .where(
            ClassMember.learner_id == learner.id,
            Assignment.due_at >= utc_now(),
        )
        .order_by(Assignment.due_at, Assignment.created_at)
    ).all()
    class_assignments = [
        HomeClassAssignmentResponse(
            assignment_id=assignment.id,
            class_id=classroom.id,
            class_name=classroom.name,
            title=assignment.title,
            skill=assignment.skill,
            content=assignment.content,
            estimated_minutes=assignment.estimated_minutes,
            due_at=_as_utc(assignment.due_at),
            submission_id=submission.id if submission else None,
            submission_status=submission.status if submission else None,
            teacher_feedback=submission.teacher_feedback if submission else None,
        )
        for assignment, classroom, submission in rows
    ]
    outstanding_minutes = sum(
        item.estimated_minutes for item in class_assignments if item.submission_status is None
    )
    daily_minutes = (
        learning_path.minutes_per_day
        if learning_path is not None
        else profile.daily_minutes
        if profile is not None and profile.daily_minutes is not None
        else 30
    )
    remaining_minutes = max(daily_minutes - outstanding_minutes, 0)
    next_personal_task = _next_personal_task(learning_path, remaining_minutes)
    personal_task_minutes = next_personal_task.duration_minutes if next_personal_task else 0
    return HomeResponse(
        goal=(
            learning_path.goal if learning_path is not None else profile.goal if profile is not None else None
        ),
        current_level=learner.level,
        daily_minutes=daily_minutes,
        class_assignment_minutes=outstanding_minutes,
        remaining_personal_minutes=remaining_minutes,
        total_planned_minutes=outstanding_minutes + personal_task_minutes,
        class_assignments=class_assignments,
        personal_learning_path=(
            LearningPathResponse.model_validate(learning_path) if learning_path is not None else None
        ),
        next_personal_task=next_personal_task,
    )
