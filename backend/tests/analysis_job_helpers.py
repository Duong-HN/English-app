import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AnalysisJob, utc_now
from app.worker import process_job


def complete_legacy_analysis(
    client: TestClient,
    token: str,
    analysis_type: str,
    payload: dict,
    extra_headers: dict[str, str] | None = None,
):
    """Exercise the legacy async alias and return its completed analysis response."""
    headers = {"Authorization": f"Bearer {token}", **(extra_headers or {})}
    queued = client.post(
        f"/api/v1/analyses/{analysis_type}",
        headers=headers,
        json=payload,
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"

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
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded", completed.text
    analysis = client.get(
        f"/api/v1/analyses/{completed.json()['analysis_id']}",
        headers=headers,
    )
    assert analysis.status_code == 200, analysis.text
    return analysis
