import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AssignmentGradingJob, utc_now
from app.worker import process_assignment_grading_job


def complete_assignment_submission(
    client: TestClient,
    assignment_id: str,
    token: str,
    input_text: str,
    *,
    idempotency_key: str | None = None,
):
    """Queue an assignment submission, run one worker attempt, and return the submission."""
    headers = {"Authorization": f"Bearer {token}"}
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    queued = client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        headers=headers,
        json={"input_text": input_text},
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"

    with SessionLocal() as db:
        job = db.scalar(select(AssignmentGradingJob).where(AssignmentGradingJob.id == queued.json()["id"]))
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()
    asyncio.run(process_assignment_grading_job(queued.json()["id"]))

    completed_job = client.get(
        f"/api/v1/assignment-grading-jobs/{queued.json()['id']}",
        headers=headers,
    )
    assert completed_job.status_code == 200, completed_job.text
    assert completed_job.json()["status"] == "succeeded", completed_job.text
    submission = client.get(
        f"/api/v1/assignments/{assignment_id}/submission",
        headers=headers,
    )
    assert submission.status_code == 200, submission.text
    assert submission.json()["status"] == "submitted", submission.text
    return submission
