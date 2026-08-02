from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_current_user
from ..learning_path_service import (
    LearningPathGenerationError,
    create_learning_path_record,
)
from ..learning_spaces import get_learning_space
from ..models import LearnerProfile, LearningPath, LearningSpace, User, utc_now
from ..schemas import (
    DailyProgressUpdate,
    LearningPathGenerateRequest,
    LearningPathJobResponse,
    LearningPathListResponse,
    LearningPathResponse,
    MessageResponse,
)
from .learning_path_jobs import enqueue_learning_path_adaptation

router = APIRouter(prefix="/learning-paths", tags=["learning paths"])


def _path_response(learning_path: LearningPath) -> LearningPathResponse:
    return LearningPathResponse.model_validate(learning_path)


@router.post("/generate", response_model=LearningPathResponse, status_code=status.HTTP_201_CREATED)
async def generate_learning_path(
    request: LearningPathGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    if space.kind != "self":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Class spaces use teacher-assigned content",
        )
    profile = db.get(LearnerProfile, user.id)
    if profile is not None and profile.onboarding_completed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete onboarding before generating another learning path",
        )
    try:
        learning_path = await create_learning_path_record(
            db,
            user,
            space=space,
            goal=request.goal,
            current_level=request.current_level,
            minutes_per_day=request.minutes_per_day,
            settings=settings,
        )
    except LearningPathGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc
    db.commit()
    db.refresh(learning_path)
    return _path_response(learning_path)


@router.get("/current", response_model=LearningPathResponse)
def current_learning_path(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath)
        .where(LearningPath.user_id == user.id, LearningPath.space_id == space.id)
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return _path_response(learning_path)


@router.get("", response_model=LearningPathListResponse)
def list_learning_paths(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    filters = (LearningPath.user_id == user.id) & (LearningPath.space_id == space.id)
    total = db.scalar(select(func.count()).select_from(LearningPath).where(filters)) or 0
    rows = db.scalars(
        select(LearningPath)
        .where(filters)
        .order_by(LearningPath.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return LearningPathListResponse(
        items=[_path_response(row) for row in rows],
        total=total,
    )


@router.get("/{learning_path_id}", response_model=LearningPathResponse)
def get_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    return _path_response(learning_path)


@router.patch("/{learning_path_id}/days/{day}", response_model=LearningPathResponse)
def update_daily_progress(
    learning_path_id: str,
    day: int,
    request: DailyProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    task_days = {
        task.get("day") for task in learning_path.plan.get("daily_tasks", []) if isinstance(task, dict)
    }
    if day not in task_days:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task day not found")

    progress = dict(learning_path.daily_progress or {})
    previous = dict(progress.get(str(day), {}))
    progress[str(day)] = {
        **previous,
        "completed": request.completed,
        "completed_at": utc_now().isoformat() if request.completed else None,
        "note": request.note,
    }
    learning_path.daily_progress = progress
    db.commit()
    db.refresh(learning_path)
    return _path_response(learning_path)


@router.post(
    "/{learning_path_id}/adapt",
    response_model=LearningPathJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def adapt_learning_path(
    learning_path_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    return enqueue_learning_path_adaptation(
        learning_path_id,
        idempotency_key=idempotency_key,
        db=db,
        user=user,
        space=space,
    )


@router.delete("/{learning_path_id}", response_model=MessageResponse)
def delete_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    db.delete(learning_path)
    db.commit()
    return MessageResponse(message="Learning path deleted")
