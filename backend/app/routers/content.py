from datetime import datetime
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..config import Settings, get_settings
from ..content_catalog import FOCUSED_COURSE_CODE, ensure_catalog
from ..db import get_db
from ..dependencies import get_current_user, require_admin
from ..learning_spaces import get_learning_space
from ..media_storage import delete_stored_media, resolve_storage_path, save_upload
from ..models import (
    AdminAuditLog,
    Course,
    CourseUnit,
    LearningSpace,
    Lesson,
    LessonMedia,
    LessonProgress,
    User,
    utc_now,
)
from ..schemas import (
    CourseLessonSummary,
    CourseListResponse,
    CourseResponse,
    CourseUnitResponse,
    LessonMediaProgressResponse,
    LessonMediaProgressUpdate,
    LessonMediaResponse,
    LessonMediaUrlCreateRequest,
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
                        media_count=len(lesson.media_items),
                    )
                    for lesson in unit.lessons
                ],
            )
            for unit in course.units
        ],
    )


def _media_url(media: LessonMedia, request: Request, settings: Settings) -> str:
    if media.source_url:
        return media.source_url
    if settings.media_public_base_url:
        return f"{settings.media_public_base_url.rstrip('/')}/api/v1/content/media/{media.id}/stream"
    return str(request.url_for("stream_lesson_media", media_id=media.id))


def _media_response(media: LessonMedia, request: Request, settings: Settings) -> LessonMediaResponse:
    return LessonMediaResponse(
        id=media.id,
        media_type=media.media_type,
        title=media.title,
        media_url=_media_url(media, request, settings),
        mime_type=media.mime_type,
        file_size_bytes=media.file_size_bytes,
        duration_seconds=media.duration_seconds,
        transcript=media.transcript,
        caption_url=media.caption_url,
        sort_order=media.sort_order,
        is_published=media.is_published,
        created_at=media.created_at,
    )


def _media_progress_response(progress: LessonProgress | None) -> dict[str, LessonMediaProgressResponse]:
    if progress is None:
        return {}
    response: dict[str, LessonMediaProgressResponse] = {}
    for media_id, value in (progress.media_progress or {}).items():
        if not isinstance(value, dict):
            continue
        updated_at = value.get("updated_at")
        try:
            parsed_updated_at = datetime.fromisoformat(updated_at) if isinstance(updated_at, str) else None
            response[str(media_id)] = LessonMediaProgressResponse(
                position_seconds=max(0, int(value.get("position_seconds", 0))),
                completed=bool(value.get("completed", False)),
                updated_at=parsed_updated_at,
            )
        except (TypeError, ValueError):
            continue
    return response


def _lesson_response(
    lesson: Lesson,
    progress: LessonProgress | None,
    request: Request,
    settings: Settings,
    *,
    include_unpublished: bool = False,
) -> LessonResponse:
    media_items = [media for media in lesson.media_items if include_unpublished or media.is_published]
    media = [_media_response(item, request, settings) for item in media_items]
    legacy_media_url = lesson.media_url or (media[0].media_url if media else None)
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
        content_pack=lesson.content_pack or {},
        source_attribution=lesson.source_attribution,
        license_name=lesson.license_name,
        media_url=legacy_media_url,
        media=media,
        duration_minutes=lesson.duration_minutes,
        progress_status=progress.status if progress else None,
        progress_score=progress.score if progress else None,
        completed_at=progress.completed_at if progress else None,
        media_progress=_media_progress_response(progress),
    )


def _lesson_query(db: Session, lesson_id: str) -> Lesson | None:
    return (
        db.execute(
            select(Lesson)
            .options(
                joinedload(Lesson.unit).joinedload(CourseUnit.course),
                joinedload(Lesson.media_items),
            )
            .where(Lesson.id == lesson_id)
        )
        .unique()
        .scalar_one_or_none()
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
        .options(joinedload(Course.units).joinedload(CourseUnit.lessons).joinedload(Lesson.media_items))
        .where(Course.active.is_(True))
    )
    if kind:
        statement = statement.where(Course.kind == kind)
    if level:
        normalized_level = level.upper()
        if normalized_level in {"A2", "B1"}:
            statement = statement.where(Course.code == FOCUSED_COURSE_CODE)
        else:
            statement = statement.where(Course.level == normalized_level)
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
    course = (
        db.execute(
            select(Course)
            .options(joinedload(Course.units).joinedload(CourseUnit.lessons).joinedload(Lesson.media_items))
            .where(Course.code == course_code, Course.active.is_(True))
        )
        .unique()
        .scalar_one_or_none()
    )
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return _course_response(course, _progress_by_lesson(db, space))


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
def get_lesson(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
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
    return _lesson_response(lesson, progress, request, settings)


@router.patch("/lessons/{lesson_id}/progress", response_model=LessonResponse)
def update_lesson_progress(
    lesson_id: str,
    request: LessonProgressUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
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
    return _lesson_response(lesson, progress, http_request, settings)


@router.patch("/lessons/{lesson_id}/media-progress", response_model=LessonResponse)
def update_media_progress(
    lesson_id: str,
    request: LessonMediaProgressUpdate,
    http_request: Request,
    db: Session = Depends(get_db),
    space: LearningSpace = Depends(get_learning_space),
    settings: Settings = Depends(get_settings),
):
    _require_self_space(space)
    ensure_catalog(db)
    lesson = _lesson_query(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    media = next(
        (item for item in lesson.media_items if item.id == request.media_id and item.is_published),
        None,
    )
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson media not found")

    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.space_id == space.id,
            LessonProgress.lesson_id == lesson.id,
        )
    )
    now = utc_now()
    media_progress = dict(progress.media_progress or {}) if progress is not None else {}
    media_progress[media.id] = {
        "position_seconds": request.position_seconds,
        "completed": request.completed,
        "updated_at": now.isoformat(),
    }
    if progress is None:
        progress = LessonProgress(
            space_id=space.id,
            lesson_id=lesson.id,
            status="started",
            media_progress=media_progress,
            started_at=now,
            updated_at=now,
        )
        db.add(progress)
    else:
        progress.media_progress = media_progress
        progress.updated_at = now
    db.commit()
    db.refresh(progress)
    return _lesson_response(lesson, progress, http_request, settings)


@router.get("/media/{media_id}/stream", name="stream_lesson_media")
def stream_lesson_media(
    media_id: str,
    range_header: str | None = Header(default=None, alias="Range"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    media = db.scalar(
        select(LessonMedia).where(
            LessonMedia.id == media_id,
            LessonMedia.is_published.is_(True),
        )
    )
    if media is None or not media.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    try:
        path = resolve_storage_path(settings, media.storage_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found") from exc
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
    if range_header:
        file_size = path.stat().st_size
        try:
            unit, value = range_header.split("=", 1)
            if unit != "bytes" or "," in value:
                raise ValueError
            start_text, end_text = value.split("-", 1)
            if start_text:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
            else:
                suffix_length = int(end_text)
                if suffix_length <= 0:
                    raise ValueError
                start = max(0, file_size - suffix_length)
                end = file_size - 1
            if start < 0 or start >= file_size or end < start:
                raise ValueError
            end = min(end, file_size - 1)
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{path.stat().st_size}"},
            ) from None

        def iter_range():
            remaining = end - start + 1
            with path.open("rb") as source:
                source.seek(start)
                while remaining > 0:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return StreamingResponse(
            iter_range(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=media.mime_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Cache-Control": "private, max-age=300",
            },
        )
    return FileResponse(
        path,
        media_type=media.mime_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/admin/courses", response_model=CourseListResponse)
def admin_list_courses(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    ensure_catalog(db)
    rows = (
        db.execute(
            select(Course)
            .options(joinedload(Course.units).joinedload(CourseUnit.lessons).joinedload(Lesson.media_items))
            .where(Course.active.is_(True))
            .order_by(Course.kind, Course.level, Course.code)
        )
        .unique()
        .scalars()
        .all()
    )
    return CourseListResponse(items=[_course_response(row) for row in rows], total=len(rows))


@router.get("/admin/lessons/{lesson_id}", response_model=LessonResponse)
def admin_get_lesson(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    ensure_catalog(db)
    lesson = _lesson_query(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return _lesson_response(lesson, None, request, settings, include_unpublished=True)


def _validate_external_media_url(source_url: str, media_type: str, mime_type: str) -> str:
    parsed = urlparse(source_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="source_url must be an http(s) URL",
        )
    if not mime_type.lower().startswith(f"{media_type}/") and mime_type.lower() not in {
        "application/vnd.apple.mpegurl",
        "application/x-mpegurl",
    }:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="mime_type does not match media_type",
        )
    return source_url.strip()


def _ensure_admin_lesson(db: Session, lesson_id: str) -> Lesson:
    ensure_catalog(db)
    lesson = _lesson_query(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


def _record_media_audit(
    db: Session,
    admin: User,
    *,
    action: str,
    media_id: str | None,
    lesson_id: str,
    media_type: str,
    title: str,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            action=action,
            target_type="lesson_media",
            target_id=media_id,
            details={
                "lesson_id": lesson_id,
                "media_type": media_type,
                "title": title,
            },
        )
    )


@router.post(
    "/admin/lessons/{lesson_id}/media",
    response_model=LessonMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_lesson_media(
    lesson_id: str,
    request: Request,
    file: UploadFile = File(...),
    media_type: str = Form(...),
    title: str = Form(...),
    transcript: str | None = Form(default=None),
    caption_url: str | None = Form(default=None),
    duration_seconds: int | None = Form(default=None),
    sort_order: int = Form(default=0),
    is_published: bool = Form(default=True),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    lesson = _ensure_admin_lesson(db, lesson_id)
    media_type = media_type.strip().lower()
    title = " ".join(title.split())
    if media_type not in {"audio", "video"} or not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid media metadata",
        )
    if duration_seconds is not None and not 1 <= duration_seconds <= 86_400:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid duration_seconds",
        )
    if not 0 <= sort_order <= 999:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid sort_order")

    try:
        stored = save_upload(file, media_type=media_type, settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

    media = LessonMedia(
        lesson_id=lesson.id,
        media_type=media_type,
        title=title,
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        file_size_bytes=stored.file_size_bytes,
        duration_seconds=duration_seconds,
        transcript=(transcript or lesson.transcript or None),
        caption_url=caption_url.strip() if caption_url else None,
        sort_order=sort_order,
        is_published=is_published,
        created_by_id=admin.id,
        created_at=utc_now(),
    )
    db.add(media)
    try:
        db.flush()
        _record_media_audit(
            db,
            admin,
            action="create_lesson_media",
            media_id=media.id,
            lesson_id=lesson.id,
            media_type=media.media_type,
            title=media.title,
        )
        db.commit()
        db.refresh(media)
    except Exception:
        db.rollback()
        delete_stored_media(settings, stored.storage_key)
        raise
    return _media_response(media, request, settings)


@router.post(
    "/admin/lessons/{lesson_id}/media/url",
    response_model=LessonMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_lesson_media_url(
    lesson_id: str,
    request: LessonMediaUrlCreateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    lesson = _ensure_admin_lesson(db, lesson_id)
    source_url = _validate_external_media_url(request.source_url, request.media_type, request.mime_type)
    media = LessonMedia(
        lesson_id=lesson.id,
        media_type=request.media_type,
        title=request.title,
        source_url=source_url,
        mime_type=request.mime_type,
        duration_seconds=request.duration_seconds,
        transcript=request.transcript or lesson.transcript,
        caption_url=request.caption_url,
        sort_order=request.sort_order,
        is_published=request.is_published,
        created_by_id=admin.id,
        created_at=utc_now(),
    )
    db.add(media)
    db.flush()
    _record_media_audit(
        db,
        admin,
        action="register_lesson_media_url",
        media_id=media.id,
        lesson_id=lesson.id,
        media_type=media.media_type,
        title=media.title,
    )
    db.commit()
    db.refresh(media)
    return _media_response(media, http_request, settings)


@router.delete("/admin/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson_media(
    media_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    settings: Settings = Depends(get_settings),
):
    media = db.get(LessonMedia, media_id)
    if media is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    storage_key = media.storage_key
    _record_media_audit(
        db,
        admin,
        action="delete_lesson_media",
        media_id=media.id,
        lesson_id=media.lesson_id,
        media_type=media.media_type,
        title=media.title,
    )
    db.delete(media)
    db.commit()
    delete_stored_media(settings, storage_key)
