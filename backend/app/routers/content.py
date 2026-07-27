from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..content_catalog import ensure_catalog
from ..db import get_db
from ..learning_spaces import get_learning_space
from ..models import Course, CourseUnit, LearningSpace, Lesson, LessonProgress, utc_now
from ..schemas import (
    CourseLessonSummary,
    CourseListResponse,
    CourseResponse,
    CourseUnitResponse,
    LessonProgressUpdate,
    LessonResponse,
)

router = APIRouter(prefix="/content", tags=["curriculum content"])


def _require_self_space(space: LearningSpace) -> None:
    if space.kind != "self":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Curriculum content is available in the self-study space",
        )


def _course_response(
    course: Course,
    progress_by_lesson: dict[str, str] | None = None,
) -> CourseResponse:
    progress_by_lesson = progress_by_lesson or {}
    return CourseResponse(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        kind=course.kind,
        level=course.level,
        band_min=course.band_min,
        band_max=course.band_max,
        units=[
            CourseUnitResponse(
                id=unit.id,
                unit_number=unit.unit_number,
                title=unit.title,
                objective=unit.objective,
                lessons=[
                    CourseLessonSummary(
                        id=lesson.id,
                        lesson_number=lesson.lesson_number,
                        title=lesson.title,
                        skill=lesson.skill,
                        content_type=lesson.content_type,
                        summary=lesson.summary,
                        duration_minutes=lesson.duration_minutes,
                        progress_status=progress_by_lesson.get(lesson.id),
                    )
                    for lesson in unit.lessons
                ],
            )
            for unit in course.units
        ],
    )


def _lesson_response(lesson: Lesson, progress: LessonProgress | None) -> LessonResponse:
    return LessonResponse(
        id=lesson.id,
        course_code=lesson.unit.course.code,
        course_title=lesson.unit.course.title,
        unit_number=lesson.unit.unit_number,
        unit_title=lesson.unit.title,
        lesson_number=lesson.lesson_number,
        title=lesson.title,
        skill=lesson.skill,
        content_type=lesson.content_type,
        summary=lesson.summary,
        body=lesson.body,
        transcript=lesson.transcript,
        media_url=lesson.media_url,
        duration_minutes=lesson.duration_minutes,
        progress_status=progress.status if progress else None,
        progress_score=progress.score if progress else None,
        completed_at=progress.completed_at if progress else None,
    )


def _lesson_query(db: Session, lesson_id: str) -> Lesson | None:
    return db.scalar(
        select(Lesson)
        .options(joinedload(Lesson.unit).joinedload(CourseUnit.course))
        .where(Lesson.id == lesson_id)
    )


def _progress_by_lesson(db: Session, space: LearningSpace) -> dict[str, str]:
    rows = db.execute(
        select(LessonProgress.lesson_id, LessonProgress.status).where(
            LessonProgress.space_id == space.id,
        )
    ).all()
    return {lesson_id: status for lesson_id, status in rows}


@router.get("/courses", response_model=CourseListResponse)
def list_courses(
    kind: str | None = Query(default=None),
    level: str | None = Query(default=None),
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
):
    _require_self_space(space)
    ensure_catalog(db)
    statement = (
        select(Course)
        .options(joinedload(Course.units).joinedload(CourseUnit.lessons))
        .where(Course.active.is_(True))
    )
    if kind:
        statement = statement.where(Course.kind == kind)
    if level:
        statement = statement.where(Course.level == level.upper())
    rows = db.execute(statement.order_by(Course.kind, Course.level, Course.code)).unique().scalars().all()
    progress = _progress_by_lesson(db, space)
    return CourseListResponse(
        items=[_course_response(row, progress) for row in rows],
        total=len(rows),
    )


@router.get("/courses/{course_code}", response_model=CourseResponse)
def get_course(
    course_code: str,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
):
    _require_self_space(space)
    ensure_catalog(db)
    course = db.scalar(
        select(Course)
        .options(joinedload(Course.units).joinedload(CourseUnit.lessons))
        .where(Course.code == course_code, Course.active.is_(True))
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return _course_response(course, _progress_by_lesson(db, space))


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def get_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
):
    _require_self_space(space)
    ensure_catalog(db)
    lesson = _lesson_query(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.space_id == space.id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    return _lesson_response(lesson, progress)


@router.patch("/lessons/{lesson_id}/progress", response_model=LessonResponse)
def update_lesson_progress(
    lesson_id: str,
    request: LessonProgressUpdate,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
):
    _require_self_space(space)
    ensure_catalog(db)
    lesson = _lesson_query(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.space_id == space.id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    now = utc_now()
    if progress is None:
        progress = LessonProgress(
            space_id=space.id,
            lesson_id=lesson.id,
            status=request.status,
            score=request.score,
            note=request.note,
            started_at=now,
            completed_at=now if request.status == "completed" else None,
            updated_at=now,
        )
        db.add(progress)
    else:
        progress.status = request.status
        progress.score = request.score
        progress.note = request.note
        progress.completed_at = now if request.status == "completed" else None
        progress.updated_at = now
    db.commit()
    db.refresh(progress)
    return _lesson_response(lesson, progress)
