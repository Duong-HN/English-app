import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_DATABASE_URL"),
    reason="Set POSTGRES_TEST_DATABASE_URL to run the PostgreSQL integration suite",
)

if os.getenv("POSTGRES_TEST_DATABASE_URL"):
    from app.worker import process_one


def test_postgres_readiness_auth_and_ai_job(client):
    email = f"pg-{uuid4().hex}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": "Postgres Learner",
        },
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": uuid4().hex}

    ready = client.get("/health/ready")
    assert ready.status_code == 200, ready.text
    job = client.post(
        "/api/v1/analysis-jobs/reading",
        headers=headers,
        json={"input_text": "The learner practices English every day."},
    )
    assert job.status_code == 202, job.text
    assert job.json()["status"] == "queued"

    assert process_one() is True
    completed = client.get(
        f"/api/v1/analysis-jobs/{job.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["analysis_id"]
