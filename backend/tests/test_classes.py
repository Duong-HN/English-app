from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.cli import create_admin
from app.models import User


def test_sqlite_foreign_keys_are_enabled(db_session):
    assert db_session.scalar(text("PRAGMA foreign_keys")) == 1


def register(client: TestClient, email: str, display_name: str = "Classroom User") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def set_role(db_session, email: str, role: str) -> str:
    user = db_session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None
    user.role = role
    db_session.commit()
    return user.id


def create_classroom(client: TestClient, teacher: dict, name: str = "English Practice") -> dict:
    response = client.post(
        "/api/v1/classes",
        headers=auth_header(teacher["access_token"]),
        json={
            "name": name,
            "description": "A focused classroom for English learners.",
            "target_level": "B1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def join_and_approve(client: TestClient, classroom: dict, learner: dict, teacher: dict) -> dict:
    joined = client.post(
        "/api/v1/classes/join",
        headers=auth_header(learner["access_token"]),
        json={"join_code": classroom["join_code"]},
    )
    assert joined.status_code == 201, joined.text
    approved = client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{joined.json()['membership_id']}",
        headers=auth_header(teacher["access_token"]),
        json={"status": "active"},
    )
    assert approved.status_code == 200, approved.text
    return approved.json()


def create_analysis(client: TestClient, learner: dict, analysis_type: str, text: str) -> dict:
    response = client.post(
        f"/api/v1/analyses/{analysis_type}",
        headers=auth_header(learner["access_token"]),
        json={"input_text": text},
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_assignment(
    client: TestClient,
    classroom: dict,
    manager: dict,
    *,
    title: str = "Weekly writing",
    status_value: str = "published",
    due_at: str | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(manager["access_token"]),
        json={
            "title": title,
            "instructions": "Write a clear paragraph and revise it after receiving feedback.",
            "skill_type": "writing",
            "target_level": "B1",
            "status": status_value,
            "due_at": due_at,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_teacher_class_management_admin_visibility_and_role_invariants(
    client,
    db_session,
    monkeypatch,
):
    teacher = register(client, "class-owner-teacher@example.com", "Owner Teacher")
    other_teacher = register(client, "class-other-teacher@example.com", "Other Teacher")
    learner = register(client, "class-role-learner@example.com", "Role Learner")
    admin = register(client, "class-role-admin@example.com", "Role Admin")
    set_role(db_session, teacher["user"]["email"], "teacher")
    other_teacher_id = set_role(db_session, other_teacher["user"]["email"], "teacher")
    set_role(db_session, admin["user"]["email"], "admin")

    assert learner["user"]["role"] == "learner"
    forbidden = client.post(
        "/api/v1/classes",
        headers=auth_header(learner["access_token"]),
        json={"name": "Learner Class", "description": "Not allowed"},
    )
    assert forbidden.status_code == 403

    classroom = create_classroom(client, teacher, "Teacher-owned B1 Class")
    assert classroom["teacher_id"] == teacher["user"]["id"]
    assert classroom["join_code"]
    assert classroom["active_member_count"] == 0
    assert classroom["pending_member_count"] == 0
    assert classroom["assignment_count"] == 0

    other_headers = auth_header(other_teacher["access_token"])
    assert client.get(f"/api/v1/classes/{classroom['id']}", headers=other_headers).status_code == 404
    assert (
        client.patch(
            f"/api/v1/classes/{classroom['id']}",
            headers=other_headers,
            json={"name": "Stolen Class"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/classes/managed", headers=other_headers).json()["total"] == 0

    admin_headers = auth_header(admin["access_token"])
    managed = client.get("/api/v1/classes/managed?limit=100", headers=admin_headers)
    assert managed.status_code == 200
    assert any(item["id"] == classroom["id"] for item in managed.json()["items"])
    moderated = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=admin_headers,
        json={"name": "Admin-moderated B1 Class"},
    )
    assert moderated.status_code == 200
    assert moderated.json()["name"] == "Admin-moderated B1 Class"

    teacher_filter = client.get("/api/v1/admin/users?role=teacher&limit=100", headers=admin_headers)
    assert teacher_filter.status_code == 200
    teacher_emails = {item["email"] for item in teacher_filter.json()["items"]}
    assert teacher["user"]["email"] in teacher_emails
    assert other_teacher["user"]["email"] in teacher_emails

    stats = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats.status_code == 200
    assert stats.json()["teacher_users"] >= 2
    assert stats.json()["total_classes"] >= 1
    assert stats.json()["active_classes"] >= 1

    blocked_role_change = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=admin_headers,
        json={"role": "learner"},
    )
    assert blocked_role_change.status_code == 409
    blocked_deactivation = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert blocked_deactivation.status_code == 409
    monkeypatch.setenv("ADMIN_PASSWORD", "cli-safe-password-123")
    with pytest.raises(SystemExit, match="active classes"):
        create_admin(teacher["user"]["email"], "Owner Teacher")
    paused = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert paused.status_code == 200
    demoted = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=admin_headers,
        json={"role": "learner"},
    )
    assert demoted.status_code == 200
    cannot_reopen = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert cannot_reopen.status_code == 409
    promoted_again = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=admin_headers,
        json={"role": "teacher"},
    )
    assert promoted_again.status_code == 200
    reopened = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=admin_headers,
        json={"is_active": True},
    )
    assert reopened.status_code == 200
    allowed_role_change = client.patch(
        f"/api/v1/admin/users/{other_teacher_id}",
        headers=admin_headers,
        json={"role": "learner"},
    )
    assert allowed_role_change.status_code == 200
    assert allowed_role_change.json()["role"] == "learner"

    audit_logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_logs.status_code == 200
    assert any(
        item["action"] == "class.updated" and item["target_id"] == classroom["id"]
        for item in audit_logs.json()["items"]
    )


def test_membership_lifecycle_join_code_rotation_and_inactive_class(client, db_session):
    teacher = register(client, "membership-teacher@example.com", "Membership Teacher")
    learner = register(client, "membership-learner@example.com", "Membership Learner")
    second = register(client, "membership-second@example.com", "Second Learner")
    third = register(client, "membership-third@example.com", "Third Learner")
    set_role(db_session, teacher["user"]["email"], "teacher")
    classroom = create_classroom(client, teacher, "Membership Lifecycle")
    learner_headers = auth_header(learner["access_token"])
    teacher_headers = auth_header(teacher["access_token"])

    invalid = client.post(
        "/api/v1/classes/join",
        headers=learner_headers,
        json={"join_code": "BADCODE1"},
    )
    assert invalid.status_code == 404

    joined = client.post(
        "/api/v1/classes/join",
        headers=learner_headers,
        json={"join_code": classroom["join_code"].lower()},
    )
    assert joined.status_code == 201
    joined_payload = joined.json()
    assert joined_payload["membership_status"] == "pending"
    assert "join_code" not in joined_payload
    duplicate = client.post(
        "/api/v1/classes/join",
        headers=learner_headers,
        json={"join_code": classroom["join_code"]},
    )
    assert duplicate.status_code == 409

    mine = client.get("/api/v1/classes/mine", headers=learner_headers)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1
    assert "join_code" not in mine.json()["items"][0]
    detail = client.get(f"/api/v1/classes/{classroom['id']}", headers=learner_headers)
    assert detail.status_code == 200
    assert detail.json()["membership_status"] == "pending"
    assert "join_code" not in detail.json()

    approved = client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{joined_payload['membership_id']}",
        headers=teacher_headers,
        json={"status": "active"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"
    removed = client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{joined_payload['membership_id']}",
        headers=teacher_headers,
        json={"status": "removed"},
    )
    assert removed.status_code == 200
    assert client.get("/api/v1/classes/mine", headers=learner_headers).json()["total"] == 0
    forced_reactivation = client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{joined_payload['membership_id']}",
        headers=teacher_headers,
        json={"status": "active"},
    )
    assert forced_reactivation.status_code == 409

    rejoined = client.post(
        "/api/v1/classes/join",
        headers=learner_headers,
        json={"join_code": classroom["join_code"]},
    )
    assert rejoined.status_code == 201
    assert rejoined.json()["membership_id"] == joined_payload["membership_id"]
    assert rejoined.json()["membership_status"] == "pending"
    client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{joined_payload['membership_id']}",
        headers=teacher_headers,
        json={"status": "active"},
    )
    left = client.delete(f"/api/v1/classes/{classroom['id']}/membership", headers=learner_headers)
    assert left.status_code == 200
    assert client.get("/api/v1/classes/mine", headers=learner_headers).json()["total"] == 0

    rotated = client.post(
        f"/api/v1/classes/{classroom['id']}/join-code/rotate",
        headers=teacher_headers,
    )
    assert rotated.status_code == 200
    assert rotated.json()["join_code"] != classroom["join_code"]
    assert rotated.json()["updated_at"]
    old_code = client.post(
        "/api/v1/classes/join",
        headers=auth_header(second["access_token"]),
        json={"join_code": classroom["join_code"]},
    )
    assert old_code.status_code == 404
    new_code = client.post(
        "/api/v1/classes/join",
        headers=auth_header(second["access_token"]),
        json={"join_code": rotated.json()["join_code"]},
    )
    assert new_code.status_code == 201

    disabled = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=teacher_headers,
        json={"is_active": False, "target_level": None},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert disabled.json()["target_level"] is None
    inactive_join = client.post(
        "/api/v1/classes/join",
        headers=auth_header(third["access_token"]),
        json={"join_code": rotated.json()["join_code"]},
    )
    assert inactive_join.status_code == 404


def test_assignments_submissions_attempts_isolation_and_analysis_delete_conflict(client, db_session):
    teacher = register(client, "assignment-teacher@example.com", "Assignment Teacher")
    other_teacher = register(client, "assignment-other-teacher@example.com", "Other Assignment Teacher")
    learner = register(client, "assignment-learner@example.com", "Assignment Learner")
    pending = register(client, "assignment-pending@example.com", "Pending Learner")
    outsider = register(client, "assignment-outsider@example.com", "Outsider Learner")
    admin = register(client, "assignment-admin@example.com", "Assignment Admin")
    set_role(db_session, teacher["user"]["email"], "teacher")
    set_role(db_session, other_teacher["user"]["email"], "teacher")
    set_role(db_session, admin["user"]["email"], "admin")

    classroom = create_classroom(client, teacher, "Writing Assignment Class")
    other_classroom = create_classroom(client, other_teacher, "Other Teacher Class")
    join_and_approve(client, classroom, learner, teacher)
    pending_join = client.post(
        "/api/v1/classes/join",
        headers=auth_header(pending["access_token"]),
        json={"join_code": classroom["join_code"]},
    )
    assert pending_join.status_code == 201
    outsider_membership = join_and_approve(client, other_classroom, outsider, other_teacher)

    cross_membership = client.patch(
        f"/api/v1/classes/{classroom['id']}/members/{outsider_membership['id']}",
        headers=auth_header(teacher["access_token"]),
        json={"status": "removed"},
    )
    assert cross_membership.status_code == 404

    assignment = create_assignment(client, classroom, teacher)
    assert assignment["submission_count"] == 0
    assert assignment["my_submission_count"] == 0
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(learner["access_token"]),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(pending["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(other_teacher["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(outsider["access_token"]),
        ).status_code
        == 404
    )

    reading = create_analysis(
        client,
        learner,
        "reading",
        "The learner reads an English article and identifies the main idea.",
    )
    first_writing = create_analysis(
        client,
        learner,
        "writing",
        "I practise English writing every day because clear communication matters.",
    )
    outsider_writing = create_analysis(
        client,
        outsider,
        "writing",
        "I am writing an analysis owned by a different learner account.",
    )

    mismatch = client.post(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": reading["id"]},
    )
    assert mismatch.status_code == 409
    cross_user = client.post(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": outsider_writing["id"]},
    )
    assert cross_user.status_code == 404

    first_submission = client.post(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": first_writing["id"]},
    )
    assert first_submission.status_code == 201, first_submission.text
    assert first_submission.json()["attempt_number"] == 1
    assert first_submission.json()["analysis"]["id"] == first_writing["id"]
    assert first_submission.json()["learner_email"] == learner["user"]["email"]

    second_writing = create_analysis(
        client,
        learner,
        "writing",
        "This is a revised second writing attempt with clearer supporting details.",
    )
    second_submission = client.post(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": second_writing["id"]},
    )
    assert second_submission.status_code == 201
    assert second_submission.json()["attempt_number"] == 2

    cross_teacher_update = client.patch(
        f"/api/v1/assignments/{assignment['id']}",
        headers=auth_header(other_teacher["access_token"]),
        json={"status": "closed"},
    )
    assert cross_teacher_update.status_code == 404
    admin_closed = client.patch(
        f"/api/v1/assignments/{assignment['id']}",
        headers=auth_header(admin["access_token"]),
        json={"status": "closed"},
    )
    assert admin_closed.status_code == 200
    assert admin_closed.json()["status"] == "closed"
    closed_attempt = client.post(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": second_writing["id"]},
    )
    assert closed_attempt.status_code == 409
    reopened_assignment = client.patch(
        f"/api/v1/assignments/{assignment['id']}",
        headers=auth_header(teacher["access_token"]),
        json={
            "title": "Weekly writing revised",
            "status": "published",
            "due_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        },
    )
    assert reopened_assignment.status_code == 200
    assert reopened_assignment.json()["title"] == "Weekly writing revised"
    assert reopened_assignment.json()["status"] == "published"
    assert reopened_assignment.json()["due_at"].endswith(("Z", "+00:00"))

    teacher_submissions = client.get(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(teacher["access_token"]),
    )
    assert teacher_submissions.status_code == 200
    assert teacher_submissions.json()["total"] == 2
    assert {item["attempt_number"] for item in teacher_submissions.json()["items"]} == {1, 2}
    assert all(item["analysis"]["type"] == "writing" for item in teacher_submissions.json()["items"])
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}/submissions",
            headers=auth_header(learner["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}/submissions",
            headers=auth_header(other_teacher["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}/submissions",
            headers=auth_header(admin["access_token"]),
        ).status_code
        == 200
    )
    audit_logs = client.get(
        "/api/v1/admin/audit-logs",
        headers=auth_header(admin["access_token"]),
    )
    assert any(
        item["action"] == "class_assignment.updated" and item["target_id"] == assignment["id"]
        for item in audit_logs.json()["items"]
    )

    learner_delete = client.delete(
        f"/api/v1/analyses/{first_writing['id']}",
        headers=auth_header(learner["access_token"]),
    )
    assert learner_delete.status_code == 409
    admin_delete = client.delete(
        f"/api/v1/admin/analyses/{first_writing['id']}",
        headers=auth_header(admin["access_token"]),
    )
    assert admin_delete.status_code == 409

    closed = create_assignment(
        client,
        classroom,
        teacher,
        title="Closed writing",
        status_value="closed",
    )
    closed_submission = client.post(
        f"/api/v1/assignments/{closed['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": second_writing["id"]},
    )
    assert closed_submission.status_code == 409

    overdue = create_assignment(
        client,
        classroom,
        teacher,
        title="Overdue writing",
        due_at=(datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )
    overdue_submission = client.post(
        f"/api/v1/assignments/{overdue['id']}/submissions",
        headers=auth_header(learner["access_token"]),
        json={"analysis_id": second_writing["id"]},
    )
    assert overdue_submission.status_code == 409

    disabled = client.patch(
        f"/api/v1/classes/{classroom['id']}",
        headers=auth_header(teacher["access_token"]),
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    inactive_assignment = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(teacher["access_token"]),
        json={
            "title": "Paused class assignment",
            "instructions": "This should be rejected while the class is paused.",
            "skill_type": "writing",
        },
    )
    assert inactive_assignment.status_code == 409
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(learner["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/classes/{classroom['id']}/assignments",
            headers=auth_header(learner["access_token"]),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(teacher["access_token"]),
        ).status_code
        == 200
    )


def test_classroom_auth_and_assignment_validation(client, db_session):
    teacher = register(client, "class-validation-teacher@example.com", "Validation Teacher")
    learner = register(client, "class-validation-learner@example.com", "Validation Learner")
    set_role(db_session, teacher["user"]["email"], "teacher")

    assert (
        client.post(
            "/api/v1/classes",
            json={"name": "No Auth Class", "description": "Authentication is required."},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/classes/join",
            headers=auth_header(teacher["access_token"]),
            json={"join_code": "ABCDEF12"},
        ).status_code
        == 403
    )
    classroom = create_classroom(client, teacher, "Validation Class")
    naive_due = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(teacher["access_token"]),
        json={
            "title": "Naive due date",
            "instructions": "This due date has no timezone and must be rejected.",
            "skill_type": "writing",
            "due_at": "2026-08-01T12:00:00",
        },
    )
    assert naive_due.status_code == 422
    assignment = create_assignment(client, classroom, teacher, title="Validated assignment")
    assert (
        client.patch(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(teacher["access_token"]),
            json={},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/assignments/{assignment['id']}",
            headers=auth_header(teacher["access_token"]),
            json={"due_at": "2026-08-02T12:00:00"},
        ).status_code
        == 422
    )
    assert (
        client.get(
            f"/api/v1/classes/{classroom['id']}",
            headers=auth_header(learner["access_token"]),
        ).status_code
        == 404
    )
