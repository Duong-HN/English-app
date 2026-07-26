from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import User


def register(client: TestClient, email: str, display_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def promote_to_admin(db_session, email: str) -> None:
    user = db_session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None
    user.role = "admin"
    db_session.commit()


def test_learner_application_requires_review_before_teacher_access(client, db_session):
    admin = register(client, "application-admin@example.com", "Application Admin")
    learner = register(client, "teacher-candidate@example.com", "Teacher Candidate")
    promote_to_admin(db_session, "application-admin@example.com")
    admin_headers = auth_header(admin["access_token"])
    learner_headers = auth_header(learner["access_token"])

    initial = client.get("/api/v1/teacher-applications/me", headers=learner_headers)
    direct_promotion = client.patch(
        f"/api/v1/admin/users/{learner['user']['id']}",
        headers=admin_headers,
        json={"role": "teacher"},
    )
    submitted = client.post(
        "/api/v1/teacher-applications",
        headers=learner_headers,
        json={
            "motivation": "I want to teach practical English and have experience mentoring new learners.",
            "organization": "LearnMate Community",
        },
    )
    pending = client.get(
        "/api/v1/admin/teacher-applications?status=pending",
        headers=admin_headers,
    )

    assert initial.status_code == 200
    assert initial.json() == {"application": None}
    assert direct_promotion.status_code == 409
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["status"] == "pending"
    assert pending.status_code == 200
    assert pending.json()["total"] == 1
    assert pending.json()["items"][0]["applicant_email"] == "teacher-candidate@example.com"

    application_id = submitted.json()["id"]
    rejected = client.patch(
        f"/api/v1/admin/teacher-applications/{application_id}",
        headers=admin_headers,
        json={"status": "rejected", "review_note": "Please add more detail about your teaching experience."},
    )
    after_rejection = client.get("/api/v1/auth/me", headers=learner_headers)
    resubmitted = client.post(
        "/api/v1/teacher-applications",
        headers=learner_headers,
        json={
            "motivation": (
                "I have taught beginner and intermediate English learners and can run "
                "weekly feedback sessions."
            ),
            "organization": "LearnMate Community",
        },
    )
    approved = client.patch(
        f"/api/v1/admin/teacher-applications/{application_id}",
        headers=admin_headers,
        json={"status": "approved", "review_note": "Approved after reviewing the updated profile."},
    )
    after_approval = client.get("/api/v1/auth/me", headers=learner_headers)
    audit_logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    second_submission = client.post(
        "/api/v1/teacher-applications",
        headers=learner_headers,
        json={"motivation": "This should no longer be accepted after teacher approval."},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert after_rejection.status_code == 200
    assert after_rejection.json()["role"] == "learner"
    assert resubmitted.status_code == 201
    assert resubmitted.json()["id"] == application_id
    assert resubmitted.json()["status"] == "pending"
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_email"] == "application-admin@example.com"
    assert after_approval.status_code == 200
    assert after_approval.json()["role"] == "teacher"
    assert second_submission.status_code == 403
    assert {item["action"] for item in audit_logs.json()["items"]} >= {
        "teacher_application.rejected",
        "teacher_application.approved",
    }


def test_only_admin_can_review_teacher_application(client, db_session):
    learner = register(client, "application-candidate-2@example.com", "Candidate Two")
    other_learner = register(client, "application-reviewer-learner@example.com", "Not An Admin")
    submitted = client.post(
        "/api/v1/teacher-applications",
        headers=auth_header(learner["access_token"]),
        json={"motivation": "I can help learners practise English conversation in a supportive group."},
    )

    response = client.patch(
        f"/api/v1/admin/teacher-applications/{submitted.json()['id']}",
        headers=auth_header(other_learner["access_token"]),
        json={"status": "approved"},
    )

    assert response.status_code == 403
