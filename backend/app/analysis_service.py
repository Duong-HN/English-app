"""Shared validation and persistence for synchronous and queued analyses."""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .content_catalog import ensure_catalog
from .models import Analysis, CourseUnit, LearningPath, LearningSpace, Lesson, User, utc_now
from .schemas import AnalysisRequest


@dataclass
class AnalysisContext:
    lesson: Lesson | None
    learning_path: LearningPath | None
    lesson_context: dict | None


def lesson_context(lesson: Lesson) -> dict:
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


def resolve_context(
    db: Session,
    request: AnalysisRequest,
    user: User,
    space: LearningSpace,
) -> AnalysisContext:
    lesson = None
    learning_path = None
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
    return AnalysisContext(
        lesson=lesson,
        learning_path=learning_path,
        lesson_context=lesson_context(lesson) if lesson else None,
    )


def persist_analysis(
    db: Session,
    user: User,
    space: LearningSpace,
    analysis_type: str,
    request: AnalysisRequest,
    context: AnalysisContext,
    result: dict,
    provider_name: str,
) -> Analysis:
    from .routers.vocabulary import upsert_analysis_vocabulary

    score = result.get("score")
    analysis = Analysis(
        user_id=user.id,
        space_id=space.id,
        type=analysis_type,
        input_text=request.input_text,
        result=result,
        score=float(score) if score is not None else None,
        provider=provider_name,
        lesson_id=context.lesson.id if context.lesson else None,
        learning_path_id=context.learning_path.id if context.learning_path else None,
        task_day=request.task_day,
    )
    db.add(analysis)
    db.flush()
    if analysis_type == "reading":
        upsert_analysis_vocabulary(db, user, analysis)
    if context.learning_path is not None and request.task_day is not None:
        progress = dict(context.learning_path.daily_progress or {})
        progress[str(request.task_day)] = {
            **dict(progress.get(str(request.task_day), {})),
            "completed": True,
            "completed_at": utc_now().isoformat(),
            "analysis_id": analysis.id,
        }
        context.learning_path.daily_progress = progress
    return analysis
