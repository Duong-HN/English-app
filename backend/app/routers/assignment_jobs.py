"""HTTP API and enqueue boundary for asynchronous classroom assignment grading."""

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import require_learner
from ..models import Assignment, AssignmentGradingJob, AssignmentSubmission, User, utc_now
from ..schemas import AssignmentGradingJobResponse

router = APIRouter(prefix="/assignment-grading-jobs", tags=["assignment grading jobs"])


def _fingerprint(assignment_id: str, learner_id: str, input_text: str) -> str:
    payload = {
        "assignment_id": assignment_id,
        "learner_id": learner_id,
        "input_text": input_text,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _clean_idempotency_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    cleaned = idempotency_key.strip()
    if not cleaned or len(cleaned) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key must contain 1 to 128 characters")
    return cleaned


def enqueue_assignment_grading_job(
    *,
    assignment: Assignment,
    learner: User,
    input_text: str,
    db: Session,
    idempotency_key: str | None,
) -> AssignmentGradingJob:
    idempotency_key = _clean_idempotency_key(idempotency_key)
    fingerprint = _fingerprint(assignment.id, learner.id, input_text)

    if idempotency_key:
        existing = db.scalar(
            select(AssignmentGradingJob).where(
                AssignmentGradingJob.learner_id == learner.id,
                AssignmentGradingJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key was already used for a different submission",
                )
            return existing

    active = db.scalar(
        select(AssignmentGradingJob).where(
            AssignmentGradingJob.assignment_id == assignment.id,
            AssignmentGradingJob.learner_id == learner.id,
            AssignmentGradingJob.status.in_(("queued", "processing")),
        )
    )
    if active is not None:
        if active.request_fingerprint == fingerprint:
            return active
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A different submission is already being graded",
        )

    submission = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.learner_id == learner.id,
        )
    )
    now = utc_now()
    if submission is None:
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            learner_id=learner.id,
            input_text=input_text,
            status="processing",
            submitted_at=now,
        )
        db.add(submission)
    else:
        submission.input_text = input_text
        submission.status = "processing"
        submission.teacher_feedback = None
        submission.feedback_at = None
        submission.submitted_at = now
        submission.updated_at = now
    db.flush()

    job = AssignmentGradingJob(
        assignment_id=assignment.id,
        learner_id=learner.id,
        submission_id=submission.id,
        skill=assignment.skill,
        input_text=input_text,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(AssignmentGradingJob).where(
                    AssignmentGradingJob.learner_id == learner.id,
                    AssignmentGradingJob.idempotency_key == idempotency_key,
                )
            )
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency-Key was already used for a different submission",
                    ) from exc
                return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A submission is already being graded",
        ) from exc
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=AssignmentGradingJobResponse)
def get_assignment_grading_job(
    job_id: str,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    job = db.scalar(
        select(AssignmentGradingJob).where(
            AssignmentGradingJob.id == job_id,
            AssignmentGradingJob.learner_id == learner.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment grading job not found")
    return job


@router.post("/{job_id}/retry", response_model=AssignmentGradingJobResponse)
def retry_assignment_grading_job(
    job_id: str,
    db: Session = Depends(get_db),
    learner: User = Depends(require_learner),
):
    job = db.scalar(
        select(AssignmentGradingJob).where(
            AssignmentGradingJob.id == job_id,
            AssignmentGradingJob.learner_id == learner.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment grading job not found")
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed assignment grading jobs can be retried",
        )
    submission = db.get(AssignmentSubmission, job.submission_id)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assignment submission is unavailable"
        )
    job.status = "queued"
    job.attempt_count = 0
    job.available_at = utc_now()
    job.started_at = None
    job.completed_at = None
    job.error_message = None
    job.updated_at = utc_now()
    submission.status = "processing"
    submission.updated_at = utc_now()
    db.commit()
    db.refresh(job)
    return job
