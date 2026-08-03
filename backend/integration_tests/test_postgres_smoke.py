import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.skipif(
    not os.getenv("POSTGRES_TEST_DATABASE_URL"),
    reason="Set POSTGRES_TEST_DATABASE_URL to run the PostgreSQL integration suite",
)

if os.getenv("POSTGRES_TEST_DATABASE_URL"):
    from app.db import SessionLocal
    from app.models import User
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


def test_postgres_assignment_submission_is_queued_and_processed(client):
    teacher_email = f"pg-teacher-{uuid4().hex}@example.com"
    learner_email = f"pg-learner-{uuid4().hex}@example.com"
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "email": teacher_email,
            "password": "safe-password-123",
            "display_name": "Postgres Teacher",
        },
    )
    learner = client.post(
        "/api/v1/auth/register",
        json={
            "email": learner_email,
            "password": "safe-password-123",
            "display_name": "Postgres Learner",
        },
    )
    assert teacher.status_code == 201, teacher.text
    assert learner.status_code == 201, learner.text

    with SessionLocal() as db:
        teacher_user = db.scalar(select(User).where(User.email == teacher_email))
        assert teacher_user is not None
        teacher_user.role = "teacher"
        db.commit()

    teacher_headers = {"Authorization": f"Bearer {teacher.json()['access_token']}"}
    learner_headers = {"Authorization": f"Bearer {learner.json()['access_token']}"}
    classroom = client.post(
        "/api/v1/classes",
        headers=teacher_headers,
        json={"name": "Postgres integration class", "description": "Assignment queue test"},
    )
    assert classroom.status_code == 201, classroom.text
    joined = client.post(
        "/api/v1/classes/join",
        headers=learner_headers,
        json={"invite_code": classroom.json()["invite_code"]},
    )
    assert joined.status_code == 200, joined.text
    assignment = client.post(
        f"/api/v1/classes/{classroom.json()['id']}/assignments",
        headers=teacher_headers,
        json={
            "title": "Postgres async writing",
            "skill": "writing",
            "content": "Write a short project update.",
            "estimated_minutes": 15,
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert assignment.status_code == 201, assignment.text
    queued = client.post(
        f"/api/v1/assignments/{assignment.json()['id']}/submit",
        headers={**learner_headers, "Idempotency-Key": uuid4().hex},
        json={"input_text": "The project is progressing well."},
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"

    assert process_one() is True
    completed = client.get(
        f"/api/v1/assignment-grading-jobs/{queued.json()['id']}",
        headers=learner_headers,
    )
    submission = client.get(
        f"/api/v1/assignments/{assignment.json()['id']}/submission",
        headers=learner_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "succeeded"
    assert submission.status_code == 200, submission.text
    assert submission.json()["status"] == "submitted"
