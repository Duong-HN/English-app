"""HTTP API for durable, asynchronous AI analysis jobs."""

import hashlib
import json

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..analysis_service import resolve_context
from ..db import get_db
from ..dependencies import get_current_user
from ..learning_spaces import get_learning_space
from ..models import AnalysisJob, LearningSpace, User
from ..schemas import AnalysisJobResponse, AnalysisRequest, AnalysisType

router = APIRouter(prefix="/analysis-jobs", tags=["analysis jobs"])


def _fingerprint(analysis_type: str, request: AnalysisRequest, space: LearningSpace) -> str:
    payload = {
        "type": analysis_type,
        "input_text": request.input_text,
        "lesson_id": request.lesson_id,
        "learning_path_id": request.learning_path_id,
        "task_day": request.task_day,
        "space_id": space.id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def enqueue_analysis_job(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 128:
            raise HTTPException(status_code=422, detail="Idempotency-Key must contain 1 to 128 characters")

    context = resolve_context(db, request, user, space)
    fingerprint = _fingerprint(analysis_type, request, space)
    if idempotency_key:
        existing = db.scalar(
            select(AnalysisJob).where(
                AnalysisJob.user_id == user.id,
                AnalysisJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key was already used for a different request",
                )
            return existing

    job = AnalysisJob(
        user_id=user.id,
        space_id=space.id,
        type=analysis_type,
        input_text=request.input_text,
        context=context.lesson_context,
        lesson_id=request.lesson_id,
        learning_path_id=request.learning_path_id,
        task_day=request.task_day,
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
            select(AnalysisJob).where(
                AnalysisJob.user_id == user.id,
                AnalysisJob.idempotency_key == idempotency_key,
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
    "/{analysis_type}",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_analysis(
    analysis_type: AnalysisType,
    request: AnalysisRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    return enqueue_analysis_job(analysis_type, request, idempotency_key, db, user, space)


@router.get("/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    space: LearningSpace = Depends(get_learning_space),
):
    job = db.scalar(
        select(AnalysisJob).where(
            AnalysisJob.id == job_id,
            AnalysisJob.user_id == user.id,
            AnalysisJob.space_id == space.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return job
