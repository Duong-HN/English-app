"""Database-backed AI worker for the prototype job boundary.

Run from the backend directory with ``python -m app.worker``. The worker is
deliberately a separate process from FastAPI so a slow provider call cannot
hold an HTTP request open. PostgreSQL row locking allows multiple workers to
claim different jobs safely; SQLite remains supported for local development.
"""

import asyncio
import logging
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai import build_provider
from .analysis_service import persist_analysis, resolve_context
from .config import get_settings
from .db import SessionLocal
from .models import AnalysisJob, LearningSpace, User, utc_now
from .schemas import AnalysisRequest

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
RETRY_DELAYS = (30, 120, 600)
STALE_AFTER_SECONDS = 900


def recover_stale_jobs(db: Session) -> None:
    stale_before = utc_now() - timedelta(seconds=STALE_AFTER_SECONDS)
    statement = select(AnalysisJob).where(
        AnalysisJob.status == "processing",
        AnalysisJob.started_at < stale_before,
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    for job in db.scalars(statement):
        if job.attempt_count < MAX_ATTEMPTS:
            job.status = "queued"
            job.available_at = utc_now()
            job.error_message = "Worker lease expired; job was returned to the queue"
        else:
            job.status = "failed"
            job.completed_at = utc_now()
            job.error_message = "Worker lease expired after maximum attempts"
        job.updated_at = utc_now()
    db.commit()


def claim_next_job(db: Session) -> str | None:
    recover_stale_jobs(db)
    statement = (
        select(AnalysisJob)
        .where(
            AnalysisJob.status == "queued",
            AnalysisJob.available_at <= utc_now(),
        )
        .order_by(AnalysisJob.created_at)
        .limit(1)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    job = db.scalar(statement)
    if job is None:
        return None
    job.status = "processing"
    job.attempt_count += 1
    job.started_at = utc_now()
    job.updated_at = utc_now()
    db.commit()
    return job.id


def _mark_failure(db: Session, job: AnalysisJob, message: str) -> None:
    job.error_message = message[:500]
    job.updated_at = utc_now()
    if job.attempt_count < MAX_ATTEMPTS:
        job.status = "queued"
        job.available_at = utc_now() + timedelta(seconds=RETRY_DELAYS[job.attempt_count - 1])
    else:
        job.status = "failed"
        job.completed_at = utc_now()
    db.commit()


async def process_job(job_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.status != "processing":
            return
        user = db.get(User, job.user_id)
        space = db.get(LearningSpace, job.space_id)
        if user is None or space is None:
            _mark_failure(db, job, "Analysis context is unavailable")
            return
        try:
            request = AnalysisRequest(
                input_text=job.input_text,
                lesson_id=job.lesson_id,
                learning_path_id=job.learning_path_id,
                task_day=job.task_day,
            )
            context = resolve_context(db, request, user, space)
            provider = build_provider(settings)
            result = await provider.analyze(
                job.type,
                request.input_text,
                context=job.context or context.lesson_context,
            )
            analysis = persist_analysis(db, user, space, job.type, request, context, result, provider.name)
            job.status = "succeeded"
            job.analysis_id = analysis.id
            job.provider = provider.name
            job.error_message = None
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("AI job failed", extra={"job_id": job_id, "attempt": job.attempt_count})
            _mark_failure(db, job, "AI provider failed; retry is scheduled when attempts remain")


def process_one() -> bool:
    with SessionLocal() as db:
        job_id = claim_next_job(db)
    if job_id is None:
        return False
    asyncio.run(process_job(job_id))
    return True


def run_forever() -> None:
    settings = get_settings()
    poll_seconds = 2.0
    logger.info("AI worker started", extra={"environment": settings.app_env})
    while True:
        if not process_one():
            time.sleep(poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
