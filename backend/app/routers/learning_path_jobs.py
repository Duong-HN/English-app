"""HTTP API for durable asynchronous learning-path generation jobs."""

import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import LearnerProfile, LearningPath, LearningPathJob, LearningSpace, User
from ..schemas import LearningPathGenerateRequest, LearningPathJobResponse

router = APIRouter(prefix="/learning-path-jobs", tags=["learning path jobs"])


def _fingerprint(request: LearningPathGenerateRequest, space: LearningSpace) -> str:
    payload = {
        "goal": request.goal,
        "current_level": request.current_level,
        "minutes_per_day": request.minutes_per_day,
        "space_id": space.id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _adapt_fingerprint(learning_path: LearningPath, space: LearningSpace) -> str:
    payload = {
        "operation": "adapt",
        "learning_path_id": learning_path.id,
        "space_id": space.id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _validate_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key must contain 1 to 128 characters")
    return cleaned


def _validate_generation_context(db: Session, user: User, space: LearningSpace) -> None:
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


@router.post("", response_model=LearningPathJobResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_learning_path(
    request: LearningPathGenerateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    _validate_generation_context(db, user, space)
    idempotency_key = _validate_idempotency_key(idempotency_key)
    fingerprint = _fingerprint(request, space)
    if idempotency_key:
        existing = db.scalar(
            select(LearningPathJob).where(
                LearningPathJob.user_id == user.id,
                LearningPathJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key was already used for a different request",
                )
            return existing

    job = LearningPathJob(
        user_id=user.id,
        space_id=space.id,
        goal=request.goal,
        current_level=request.current_level,
        minutes_per_day=request.minutes_per_day,
        operation="generate",
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.scalar(
            select(LearningPathJob).where(
                LearningPathJob.user_id == user.id,
                LearningPathJob.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used for a different request",
            ) from exc
        return existing
    db.refresh(job)
    return job


def enqueue_learning_path_adaptation(
    learning_path_id: str,
    *,
    idempotency_key: str | None,
    db: Session,
    user: User,
    space: LearningSpace,
) -> LearningPathJob:
    learning_path = db.scalar(
        select(LearningPath).where(
            LearningPath.id == learning_path_id,
            LearningPath.user_id == user.id,
            LearningPath.space_id == space.id,
        )
    )
    if learning_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path not found")

    idempotency_key = _validate_idempotency_key(idempotency_key)
    fingerprint = _adapt_fingerprint(learning_path, space)
    if idempotency_key:
        existing = db.scalar(
            select(LearningPathJob).where(
                LearningPathJob.user_id == user.id,
                LearningPathJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key was already used for a different request",
                )
            return existing

    job = LearningPathJob(
        user_id=user.id,
        space_id=space.id,
        goal=learning_path.goal,
        current_level=learning_path.current_level,
        minutes_per_day=learning_path.minutes_per_day,
        operation="adapt",
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        learning_path_id=learning_path.id,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.scalar(
            select(LearningPathJob).where(
                LearningPathJob.user_id == user.id,
                LearningPathJob.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used for a different request",
            ) from exc
        return existing
    db.refresh(job)
    return job


@router.post(
    "/{learning_path_id}/adapt",
    response_model=LearningPathJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_adaptation(
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


@router.get("/{job_id}", response_model=LearningPathJobResponse)
def get_learning_path_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    job = db.scalar(
        select(LearningPathJob).where(
            LearningPathJob.id == job_id,
            LearningPathJob.user_id == user.id,
            LearningPathJob.space_id == space.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path job not found")
    return job
