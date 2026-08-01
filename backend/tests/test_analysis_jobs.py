import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AnalysisJob, utc_now
from app.worker import process_job


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": "Job Learner",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_analysis_job_is_idempotent_and_processed_by_worker(client):
    session = _register(client, f"job-{uuid4().hex}@example.com")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "job-test-1",
    }
    payload = {"input_text": "The learner practices English every day."}
    queued = client.post("/api/v1/analysis-jobs/reading", headers=headers, json=payload)
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"

    duplicate = client.post("/api/v1/analysis-jobs/reading", headers=headers, json=payload)
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["id"] == queued.json()["id"]

    conflict = client.post(
        "/api/v1/analysis-jobs/reading",
        headers=headers,
        json={"input_text": "This is a different learner submission."},
    )
    assert conflict.status_code == 409, conflict.text

    with SessionLocal() as db:
        job = db.scalar(select(AnalysisJob).where(AnalysisJob.id == queued.json()["id"]))
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()
    asyncio.run(process_job(queued.json()["id"]))
    completed = client.get(
        f"/api/v1/analysis-jobs/{queued.json()['id']}",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["analysis_id"]

    analysis = client.get(
        f"/api/v1/analyses/{completed.json()['analysis_id']}",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert analysis.status_code == 200, analysis.text
