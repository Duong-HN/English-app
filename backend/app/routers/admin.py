from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from ..db import get_db
from ..dependencies import require_admin
from ..models import (
    AdminAuditLog,
    Analysis,
    AnalysisJob,
    Classroom,
    LearningPath,
    TeacherApplication,
    User,
    utc_now,
)
from ..schemas import (
    AdminAnalysisJobListResponse,
    AdminAnalysisJobResponse,
    AdminAnalysisListResponse,
    AdminAnalysisResponse,
    AdminAuditLogListResponse,
    AdminAuditLogResponse,
    AdminLearningPathListResponse,
    AdminLearningPathResponse,
    AdminStatsResponse,
    AdminStatsTrendItem,
    AdminTeacherApplicationListResponse,
    AdminTeacherApplicationResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
    AnalysisJobStatus,
    AnalysisType,
    MessageResponse,
    TeacherApplicationReview,
)

router = APIRouter(prefix="/admin", tags=["administration"])


def _user_response(user: User, analysis_count: int) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        analysis_count=analysis_count,
    )


def _analysis_response(analysis: Analysis, user: User) -> AdminAnalysisResponse:
    return AdminAnalysisResponse(
        id=analysis.id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        type=analysis.type,
        input_text=analysis.input_text,
        result=analysis.result,
        score=analysis.score,
        provider=analysis.provider,
        lesson_id=analysis.lesson_id,
        learning_path_id=analysis.learning_path_id,
        task_day=analysis.task_day,
        created_at=analysis.created_at,
    )


def _analysis_job_response(job: AnalysisJob, user: User) -> AdminAnalysisJobResponse:
    return AdminAnalysisJobResponse(
        id=job.id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        type=job.type,
        status=job.status,
        analysis_id=job.analysis_id,
        provider=job.provider,
        error_message=job.error_message,
        attempt_count=job.attempt_count,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        updated_at=job.updated_at,
    )


def _learning_path_response(learning_path: LearningPath, user: User) -> AdminLearningPathResponse:
    return AdminLearningPathResponse(
        id=learning_path.id,
        user_id=user.id,
        user_email=user.email,
        user_display_name=user.display_name,
        goal=learning_path.goal,
        current_level=learning_path.current_level,
        minutes_per_day=learning_path.minutes_per_day,
        plan=learning_path.plan,
        daily_progress=learning_path.daily_progress,
        level_source=learning_path.level_source,
        placement_attempt_id=learning_path.placement_attempt_id,
        provider=learning_path.provider,
        created_at=learning_path.created_at,
    )


def _teacher_application_response(
    application: TeacherApplication,
    applicant: User,
    reviewer: User | None,
) -> AdminTeacherApplicationResponse:
    return AdminTeacherApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        motivation=application.motivation,
        organization=application.organization,
        status=application.status,
        review_note=application.review_note,
        requested_at=application.requested_at,
        reviewed_at=application.reviewed_at,
        applicant_email=applicant.email,
        applicant_display_name=applicant.display_name,
        reviewer_email=reviewer.email if reviewer is not None else None,
    )


def _record_audit(
    db: Session,
    admin: User,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    details: dict,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


def _ensure_another_active_admin(db: Session, target: User, update: AdminUserUpdate) -> None:
    removes_admin_access = target.role == "admin" and (
        (update.role is not None and update.role != "admin") or update.is_active is False
    )
    if not removes_admin_access:
        return
    active_admins = (
        db.scalar(
            select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))
        )
        or 0
    )
    if active_admins <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active administrator cannot be disabled or demoted",
        )


def _ensure_teacher_has_no_owned_classes(db: Session, target: User, update: AdminUserUpdate) -> None:
    removes_teacher_access = target.role == "teacher" and (
        (update.role is not None and update.role != "teacher") or update.is_active is False
    )
    if not removes_teacher_access:
        return
    owned_classes = (
        db.scalar(select(func.count()).select_from(Classroom).where(Classroom.teacher_id == target.id)) or 0
    )
    if owned_classes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer or remove the teacher's classes before changing teacher access",
        )


@router.get("/stats", response_model=AdminStatsResponse)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    today = datetime.combine(date.today(), time.min, tzinfo=UTC)
    seven_days_ago = today - timedelta(days=6)

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    admin_users = db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0
    new_users = (
        db.scalar(select(func.count()).select_from(User).where(User.created_at >= seven_days_ago)) or 0
    )
    total_analyses = db.scalar(select(func.count()).select_from(Analysis)) or 0
    analyses_today = (
        db.scalar(select(func.count()).select_from(Analysis).where(Analysis.created_at >= today)) or 0
    )
    total_learning_paths = db.scalar(select(func.count()).select_from(LearningPath)) or 0
    learning_paths_today = (
        db.scalar(select(func.count()).select_from(LearningPath).where(LearningPath.created_at >= today)) or 0
    )

    type_rows = db.execute(select(Analysis.type, func.count()).group_by(Analysis.type)).all()
    analyses_by_type = {"reading": 0, "writing": 0, "speaking": 0}
    analyses_by_type.update({analysis_type: count for analysis_type, count in type_rows})

    date_column = func.date(Analysis.created_at)
    trend_rows = db.execute(
        select(date_column, func.count()).where(Analysis.created_at >= seven_days_ago).group_by(date_column)
    ).all()
    trend_by_date = {str(day): count for day, count in trend_rows}
    trend = [
        AdminStatsTrendItem(
            date=(seven_days_ago + timedelta(days=index)).date().isoformat(),
            count=trend_by_date.get((seven_days_ago + timedelta(days=index)).date().isoformat(), 0),
        )
        for index in range(7)
    ]
    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        new_users_last_7_days=new_users,
        total_analyses=total_analyses,
        analyses_today=analyses_today,
        total_learning_paths=total_learning_paths,
        learning_paths_today=learning_paths_today,
        analyses_by_type=analyses_by_type,
        analyses_last_7_days=trend,
    )


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    q: str | None = Query(default=None, max_length=120),
    role: str | None = Query(default=None, pattern="^(learner|teacher|admin)$"),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filters = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        filters.append(or_(func.lower(User.email).like(needle), func.lower(User.display_name).like(needle)))
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active.is_(is_active))

    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    counts = (
        select(Analysis.user_id, func.count(Analysis.id).label("analysis_count"))
        .group_by(Analysis.user_id)
        .subquery()
    )
    rows = db.execute(
        select(User, func.coalesce(counts.c.analysis_count, 0))
        .outerjoin(counts, counts.c.user_id == User.id)
        .where(*filters)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminUserListResponse(
        items=[_user_response(user, int(analysis_count)) for user, analysis_count in rows],
        total=total,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    update: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id and (
        update.is_active is False or (update.role is not None and update.role != "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Administrators cannot remove their own access",
        )
    _ensure_another_active_admin(db, target, update)
    _ensure_teacher_has_no_owned_classes(db, target, update)
    if update.role == "teacher" and target.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Teacher access is granted by approving a teacher application",
        )

    changes: dict[str, dict[str, str | bool]] = {}
    if update.is_active is not None and update.is_active != target.is_active:
        changes["is_active"] = {"from": target.is_active, "to": update.is_active}
        target.is_active = update.is_active
    if update.role is not None and update.role != target.role:
        changes["role"] = {"from": target.role, "to": update.role}
        target.role = update.role
    if not changes:
        return _user_response(
            target,
            db.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id == target.id)) or 0,
        )

    target.updated_at = utc_now()
    _record_audit(
        db,
        admin,
        action="user.updated",
        target_type="user",
        target_id=target.id,
        details={"changes": changes},
    )
    db.commit()
    db.refresh(target)
    analysis_count = (
        db.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id == target.id)) or 0
    )
    return _user_response(target, analysis_count)


@router.get(
    "/teacher-applications",
    response_model=AdminTeacherApplicationListResponse,
)
def list_teacher_applications(
    application_status: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending|approved|rejected)$",
    ),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filters = []
    if application_status:
        filters.append(TeacherApplication.status == application_status)

    applicant = aliased(User)
    reviewer = aliased(User)
    total = db.scalar(select(func.count()).select_from(TeacherApplication).where(*filters)) or 0
    rows = db.execute(
        select(TeacherApplication, applicant, reviewer)
        .join(applicant, TeacherApplication.user_id == applicant.id)
        .outerjoin(reviewer, TeacherApplication.reviewed_by_id == reviewer.id)
        .where(*filters)
        .order_by(TeacherApplication.requested_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminTeacherApplicationListResponse(
        items=[
            _teacher_application_response(item, applicant_user, reviewer_user)
            for item, applicant_user, reviewer_user in rows
        ],
        total=total,
    )


@router.patch(
    "/teacher-applications/{application_id}",
    response_model=AdminTeacherApplicationResponse,
)
def review_teacher_application(
    application_id: str,
    review: TeacherApplicationReview,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    application = db.get(TeacherApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher application not found")
    if application.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending teacher applications can be reviewed",
        )

    applicant = db.get(User, application.user_id)
    if applicant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Applicant not found")
    if not applicant.is_active or applicant.role != "learner":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Applicant must remain an active learner until the application is reviewed",
        )

    now = utc_now()
    application.status = review.status
    application.review_note = review.review_note
    application.reviewed_by_id = admin.id
    application.reviewed_at = now
    application.updated_at = now
    if review.status == "approved":
        applicant.role = "teacher"
        applicant.updated_at = now

    _record_audit(
        db,
        admin,
        action=f"teacher_application.{review.status}",
        target_type="teacher_application",
        target_id=application.id,
        details={
            "applicant_id": applicant.id,
            "status": review.status,
            "review_note": review.review_note,
        },
    )
    db.commit()
    db.refresh(application)
    return _teacher_application_response(application, applicant, admin)


@router.get("/analyses", response_model=AdminAnalysisListResponse)
def list_analyses(
    q: str | None = Query(default=None, max_length=200),
    analysis_type: AnalysisType | None = Query(default=None, alias="type"),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filters = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        filters.append(or_(func.lower(Analysis.input_text).like(needle), func.lower(User.email).like(needle)))
    if analysis_type:
        filters.append(Analysis.type == analysis_type)
    if user_id:
        filters.append(Analysis.user_id == user_id)

    total = db.scalar(select(func.count()).select_from(Analysis).join(User).where(*filters)) or 0
    rows = db.execute(
        select(Analysis, User)
        .join(User)
        .where(*filters)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminAnalysisListResponse(
        items=[_analysis_response(analysis, user) for analysis, user in rows],
        total=total,
    )


@router.get("/analysis-jobs", response_model=AdminAnalysisJobListResponse)
def list_analysis_jobs(
    job_status: AnalysisJobStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filters = [AnalysisJob.user_id == User.id]
    if job_status:
        filters.append(AnalysisJob.status == job_status)
    total = db.scalar(select(func.count()).select_from(AnalysisJob).join(User).where(*filters)) or 0
    rows = db.execute(
        select(AnalysisJob, User)
        .join(User)
        .where(*filters)
        .order_by(AnalysisJob.created_at.desc(), AnalysisJob.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminAnalysisJobListResponse(
        items=[_analysis_job_response(job, user) for job, user in rows],
        total=total,
    )


@router.post("/analysis-jobs/{job_id}/retry", response_model=AdminAnalysisJobResponse)
def retry_analysis_job(
    job_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    row = db.execute(select(AnalysisJob, User).join(User).where(AnalysisJob.id == job_id)).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    job, user = row
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed analysis jobs can be retried",
        )
    job.status = "queued"
    job.attempt_count = 0
    job.available_at = utc_now()
    job.started_at = None
    job.completed_at = None
    job.error_message = None
    job.updated_at = utc_now()
    _record_audit(
        db,
        admin,
        action="analysis_job.retried",
        target_type="analysis_job",
        target_id=job.id,
        details={"user_id": user.id, "analysis_type": job.type},
    )
    db.commit()
    db.refresh(job)
    return _analysis_job_response(job, user)


@router.get("/analyses/{analysis_id}", response_model=AdminAnalysisResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.execute(select(Analysis, User).join(User).where(Analysis.id == analysis_id)).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return _analysis_response(*row)


@router.delete("/analyses/{analysis_id}", response_model=MessageResponse)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    _record_audit(
        db,
        admin,
        action="analysis.deleted",
        target_type="analysis",
        target_id=analysis.id,
        details={"user_id": analysis.user_id, "analysis_type": analysis.type},
    )
    db.delete(analysis)
    db.commit()
    return MessageResponse(message="Analysis deleted by administrator")


@router.get("/learning-paths", response_model=AdminLearningPathListResponse)
def list_learning_paths(
    q: str | None = Query(default=None, max_length=200),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filters = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(LearningPath.goal).like(needle),
                func.lower(User.email).like(needle),
                func.lower(User.display_name).like(needle),
            )
        )
    if user_id:
        filters.append(LearningPath.user_id == user_id)

    total = db.scalar(select(func.count()).select_from(LearningPath).join(User).where(*filters)) or 0
    rows = db.execute(
        select(LearningPath, User)
        .join(User)
        .where(*filters)
        .order_by(LearningPath.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminLearningPathListResponse(
        items=[_learning_path_response(learning_path, user) for learning_path, user in rows],
        total=total,
    )


@router.delete("/learning-paths/{learning_path_id}", response_model=MessageResponse)
def delete_learning_path(
    learning_path_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    learning_path = db.get(LearningPath, learning_path_id)
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")
    _record_audit(
        db,
        admin,
        action="learning_path.deleted",
        target_type="learning_path",
        target_id=learning_path.id,
        details={"user_id": learning_path.user_id, "current_level": learning_path.current_level},
    )
    db.delete(learning_path)
    db.commit()
    return MessageResponse(message="Learning path deleted by administrator")


@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    total = db.scalar(select(func.count()).select_from(AdminAuditLog)) or 0
    rows = db.execute(
        select(AdminAuditLog, User)
        .outerjoin(User, User.id == AdminAuditLog.admin_user_id)
        .order_by(AdminAuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AdminAuditLogListResponse(
        items=[
            AdminAuditLogResponse(
                id=log.id,
                admin_user_id=log.admin_user_id,
                admin_email=user.email if user else None,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                details=log.details,
                created_at=log.created_at,
            )
            for log, user in rows
        ],
        total=total,
    )
