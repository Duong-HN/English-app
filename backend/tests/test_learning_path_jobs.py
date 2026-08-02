import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import LearnerProfile, LearningPathJob, utc_now
from app.worker import process_learning_path_job


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": "Async Path Learner",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_onboarding(user_id: str) -> None:
    with SessionLocal() as db:
        profile = db.get(LearnerProfile, user_id)
        assert profile is not None
        profile.onboarding_completed_at = utc_now()
        db.commit()


def test_learning_path_job_is_idempotent_and_processed_by_worker(client):
    session = _register(client, f"async-path-{uuid4().hex}@example.com")
    _complete_onboarding(session["user"]["id"])
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "learning-path-test-1",
    }
    payload = {
        "goal": "Communicate confidently at work",
        "current_level": "B1",
        "minutes_per_day": 30,
    }

    queued = client.post("/api/v1/learning-path-jobs", headers=headers, json=payload)
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"

    duplicate = client.post("/api/v1/learning-path-jobs", headers=headers, json=payload)
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["id"] == queued.json()["id"]

    conflict = client.post(
        "/api/v1/learning-path-jobs",
        headers=headers,
        json={**payload, "minutes_per_day": 45},
    )
    assert conflict.status_code == 409, conflict.text

    with SessionLocal() as db:
        job = db.scalar(select(LearningPathJob).where(LearningPathJob.id == queued.json()["id"]))
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()

    asyncio.run(process_learning_path_job(queued.json()["id"]))
    completed = client.get(
        f"/api/v1/learning-path-jobs/{queued.json()['id']}",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["learning_path_id"]

    path = client.get(
        f"/api/v1/learning-paths/{completed.json()['learning_path_id']}",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert path.status_code == 200, path.text
    assert path.json()["goal"] == payload["goal"]
    assert len(path.json()["plan"]["daily_tasks"]) == 7

    adapt_headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "learning-path-adapt-test-1",
    }
    adaptation = client.post(
        f"/api/v1/learning-path-jobs/{completed.json()['learning_path_id']}/adapt",
        headers=adapt_headers,
    )
    assert adaptation.status_code == 202, adaptation.text
    assert adaptation.json()["operation"] == "adapt"
    duplicate_adaptation = client.post(
        f"/api/v1/learning-path-jobs/{completed.json()['learning_path_id']}/adapt",
        headers=adapt_headers,
    )
    assert duplicate_adaptation.status_code == 202
    assert duplicate_adaptation.json()["id"] == adaptation.json()["id"]

    with SessionLocal() as db:
        job = db.get(LearningPathJob, adaptation.json()["id"])
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()
    asyncio.run(process_learning_path_job(adaptation.json()["id"]))
    completed_adaptation = client.get(
        f"/api/v1/learning-path-jobs/{adaptation.json()['id']}",
        headers=adapt_headers,
    )
    assert completed_adaptation.status_code == 200
    assert completed_adaptation.json()["status"] == "succeeded"
