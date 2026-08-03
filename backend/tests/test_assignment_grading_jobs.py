import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Analysis, AssignmentGradingJob, User, utc_now
from app.worker import process_assignment_grading_job


def register(client: TestClient, email: str, display_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_assignment_submission_is_queued_and_idempotent(client, db_session):
    teacher = register(client, "async-assignment-teacher@example.com", "Assignment Teacher")
    learner = register(client, "async-assignment-learner@example.com", "Assignment Learner")
    db_session.scalar(select(User).where(User.id == teacher["user"]["id"])).role = "teacher"
    db_session.commit()

    classroom = client.post(
        "/api/v1/classes",
        headers=auth_header(teacher["access_token"]),
        json={"name": "Async Assignment Class", "description": "Queue test"},
    )
    assert classroom.status_code == 201, classroom.text
    joined = client.post(
        "/api/v1/classes/join",
        headers=auth_header(learner["access_token"]),
        json={"invite_code": classroom.json()["invite_code"]},
    )
    assert joined.status_code == 200, joined.text
    assignment = client.post(
        f"/api/v1/classes/{classroom.json()['id']}/assignments",
        headers=auth_header(teacher["access_token"]),
        json={
            "title": "Async writing",
            "skill": "writing",
            "content": "Write a short project update.",
            "estimated_minutes": 20,
            "due_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert assignment.status_code == 201, assignment.text

    headers = {
        **auth_header(learner["access_token"]),
        "Idempotency-Key": "assignment-submit-1",
    }
    payload = {"input_text": "The project is progressing well."}
    queued = client.post(
        f"/api/v1/assignments/{assignment.json()['id']}/submit",
        headers=headers,
        json=payload,
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"
    assert queued.json()["analysis_id"] is None

    pending = client.get(
        f"/api/v1/assignments/{assignment.json()['id']}/submission",
        headers=auth_header(learner["access_token"]),
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "processing"
    assert pending.json()["analysis"] is None

    duplicate = client.post(
        f"/api/v1/assignments/{assignment.json()['id']}/submit",
        headers=headers,
        json=payload,
    )
    assert duplicate.status_code == 202, duplicate.text
    assert duplicate.json()["id"] == queued.json()["id"]

    conflict = client.post(
        f"/api/v1/assignments/{assignment.json()['id']}/submit",
        headers=headers,
        json={"input_text": "This is a different submission."},
    )
    assert conflict.status_code == 409, conflict.text

    with SessionLocal() as db:
        job = db.get(AssignmentGradingJob, queued.json()["id"])
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()
    asyncio.run(process_assignment_grading_job(queued.json()["id"]))

    completed = client.get(
        f"/api/v1/assignment-grading-jobs/{queued.json()['id']}",
        headers=auth_header(learner["access_token"]),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"
    assert completed.json()["analysis_id"]

    submission = client.get(
        f"/api/v1/assignments/{assignment.json()['id']}/submission",
        headers=auth_header(learner["access_token"]),
    )
    assert submission.status_code == 200
    assert submission.json()["status"] == "submitted"
    assert submission.json()["analysis"]["type"] == "writing"
    assert (
        db_session.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.user_id == learner["user"]["id"])
        )
        == 1
    )
