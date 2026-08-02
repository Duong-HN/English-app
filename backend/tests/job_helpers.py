import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import LearningPathJob, utc_now
from app.worker import process_learning_path_job


def complete_legacy_learning_path(
    client: TestClient,
    token: str,
    payload: dict,
) -> dict:
    """Exercise the legacy async alias and return its completed path."""
    headers = {"Authorization": f"Bearer {token}"}
    queued = client.post(
        "/api/v1/learning-paths/generate",
        headers=headers,
        json=payload,
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["operation"] == "generate"

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
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded", completed.text
    path = client.get(
        f"/api/v1/learning-paths/{completed.json()['learning_path_id']}",
        headers=headers,
    )
    assert path.status_code == 200, path.text
    return path.json()
