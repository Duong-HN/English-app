from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user, require_learner_only
from ..models import TeacherApplication, User, utc_now
from ..schemas import (
    TeacherApplicationCreate,
    TeacherApplicationResponse,
    TeacherApplicationStatusResponse,
)

router = APIRouter(prefix="/teacher-applications", tags=["teacher applications"])


@router.get("/me", response_model=TeacherApplicationStatusResponse)
def my_teacher_application(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    application = db.scalar(select(TeacherApplication).where(TeacherApplication.user_id == user.id))
    return TeacherApplicationStatusResponse(
        application=(
            TeacherApplicationResponse.model_validate(application) if application is not None else None
        )
    )


@router.post("", response_model=TeacherApplicationResponse, status_code=status.HTTP_201_CREATED)
def submit_teacher_application(
    request: TeacherApplicationCreate,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner_only),
):
    application = db.scalar(select(TeacherApplication).where(TeacherApplication.user_id == learner.id))
    if application is not None and application.status != "rejected":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A teacher application is already pending or approved",
        )

    if application is None:
        application = TeacherApplication(
            user_id=learner.id,
            motivation=request.motivation,
            organization=request.organization,
            status="pending",
        )
        db.add(application)
    else:
        application.motivation = request.motivation
        application.organization = request.organization
        application.status = "pending"
        application.review_note = None
        application.reviewed_by_id = None
        application.requested_at = utc_now()
        application.reviewed_at = None
        application.updated_at = utc_now()

    db.commit()
    db.refresh(application)
    return TeacherApplicationResponse.model_validate(application)
