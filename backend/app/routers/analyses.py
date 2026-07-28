from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..ai import build_provider
from ..config import Settings, get_settings
from ..content_catalog import ensure_catalog
from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import Analysis, CourseUnit, LearningPath, LearningSpace, Lesson, User, utc_now
from ..schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisType,
    HistoryResponse,
    MessageResponse,
)
from .vocabulary import upsert_analysis_vocabulary

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _lesson_context(lesson: Lesson) -> dict:
    return {
        "course_code": lesson.unit.course.code,
        "course_title": lesson.unit.course.title,
        "level": lesson.unit.course.level,
        "unit_number": lesson.unit.unit_number,
        "unit_title": lesson.unit.title,
        "lesson_number": lesson.lesson_number,
        "lesson_title": lesson.title,
        "skill": lesson.skill,
        "content_type": lesson.content_type,
        "summary": lesson.summary,
        "lesson_body": lesson.body,
        "lesson_transcript": lesson.transcript,
        "content_pack": lesson.content_pack or {},
        "source_attribution": lesson.source_attribution,
        "license_name": lesson.license_name,
        "media": [
            {
                "title": media.title,
                "media_type": media.media_type,
                "transcript": media.transcript,
            }
            for media in lesson.media_items
            if media.is_published
        ],
    }


@router.post("/{analysis_type}", response_model=AnalysisResponse)
async def create_analysis(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    learning_path = None
    lesson = None
    if request.lesson_id:
        if space.kind != "self":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Curriculum lesson context is available in the self-study space",
            )
        ensure_catalog(db)
        lesson = (
            db.execute(
                select(Lesson)
                .options(
                    joinedload(Lesson.unit).joinedload(CourseUnit.course),
                    joinedload(Lesson.media_items),
                )
                .where(Lesson.id == request.lesson_id)
            )
            .unique()
            .scalar_one_or_none()
        )
        if lesson is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    if request.learning_path_id:
        learning_path = db.scalar(
            select(LearningPath).where(
                LearningPath.id == request.learning_path_id,
                LearningPath.user_id == user.id,
                LearningPath.space_id == space.id,
            )
        )
        if learning_path is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
        if request.task_day is not None:
            task_days = {
                task.get("day")
                for task in learning_path.plan.get("daily_tasks", [])
                if isinstance(task, dict)
            }
            if request.task_day not in task_days:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Task day not found",
                )

    try:
        provider = build_provider(settings)
        if lesson is None:
            result = await provider.analyze(analysis_type, request.input_text)
        else:
            result = await provider.analyze(
                analysis_type,
                request.input_text,
                context=_lesson_context(lesson),
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider failed") from exc

    score = result.get("score")
    analysis = Analysis(
        user_id=user.id,
        space_id=space.id,
        type=analysis_type,
        input_text=request.input_text,
        result=result,
        score=float(score) if score is not None else None,
        provider=provider.name,
        lesson_id=lesson.id if lesson else None,
        learning_path_id=learning_path.id if learning_path else None,
        task_day=request.task_day,
    )
    db.add(analysis)
    db.flush()
    if analysis_type == "reading":
        upsert_analysis_vocabulary(db, user, analysis)
    if learning_path is not None and request.task_day is not None:
        progress = dict(learning_path.daily_progress or {})
        progress[str(request.task_day)] = {
            **dict(progress.get(str(request.task_day), {})),
            "completed": True,
            "completed_at": utc_now().isoformat(),
            "analysis_id": analysis.id,
        }
        learning_path.daily_progress = progress
    db.commit()
    db.refresh(analysis)
    return AnalysisResponse.model_validate(analysis)


@router.get("", response_model=HistoryResponse)
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    filters = (Analysis.user_id == user.id) & (Analysis.space_id == space.id)
    total = db.scalar(select(func.count()).select_from(Analysis).where(filters)) or 0
    rows = db.scalars(
        select(Analysis).where(filters).order_by(Analysis.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return HistoryResponse(
        items=[AnalysisResponse.model_validate(row) for row in rows],
        total=total,
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
            Analysis.space_id == space.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return AnalysisResponse.model_validate(analysis)


@router.delete("/{analysis_id}", response_model=MessageResponse)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    analysis = db.scalar(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user.id,
            Analysis.space_id == space.id,
        )
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    db.delete(analysis)
    db.commit()
    return MessageResponse(message="Analysis deleted")
