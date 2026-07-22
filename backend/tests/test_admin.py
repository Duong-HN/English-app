from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.cli import create_admin
from app.models import User


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Admin Test"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def promote(db_session, email: str, role: str = "admin") -> None:
    user = db_session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None
    user.role = role
    db_session.commit()


def test_admin_cli_creates_real_administrator(db_session, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "cli-safe-password-123")
    create_admin("cli-admin@example.com", "CLI Administrator")
    db_session.expire_all()

    user = db_session.scalar(select(User).where(User.email == "cli-admin@example.com"))
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True


def test_learner_cannot_access_admin_api(client):
    learner = register(client, "forbidden-admin@example.com")
    response = client.get(
        "/api/v1/admin/stats",
        headers=auth_header(learner["access_token"]),
    )
    assert response.status_code == 403


def test_admin_can_view_stats_and_search_users(client, db_session):
    admin = register(client, "stats-admin@example.com")
    register(client, "searchable-learner@example.com")
    teacher = register(client, "stats-teacher@example.com")
    promote(db_session, "stats-admin@example.com")
    promote(db_session, "stats-teacher@example.com", "teacher")
    headers = auth_header(admin["access_token"])

    stats = client.get("/api/v1/admin/stats", headers=headers)
    users = client.get("/api/v1/admin/users?q=searchable", headers=headers)

    assert stats.status_code == 200
    assert stats.json()["total_users"] >= 2
    assert stats.json()["total_learning_paths"] >= 0
    assert stats.json()["teacher_users"] >= 1
    assert stats.json()["total_classes"] >= 0
    assert stats.json()["active_classes"] >= 0
    assert len(stats.json()["analyses_last_7_days"]) == 7
    assert users.status_code == 200
    assert users.json()["total"] == 1
    assert users.json()["items"][0]["email"] == "searchable-learner@example.com"
    teachers = client.get("/api/v1/admin/users?role=teacher", headers=headers)
    assert teachers.status_code == 200
    assert any(item["id"] == teacher["user"]["id"] for item in teachers.json()["items"])


def test_admin_can_disable_user_and_action_is_audited(client, db_session):
    admin = register(client, "manage-admin@example.com")
    learner = register(client, "managed-learner@example.com")
    promote(db_session, "manage-admin@example.com")
    headers = auth_header(admin["access_token"])

    update = client.patch(
        f"/api/v1/admin/users/{learner['user']['id']}",
        headers=headers,
        json={"is_active": False},
    )
    unavailable = client.get(
        "/api/v1/auth/me",
        headers=auth_header(learner["access_token"]),
    )
    logs = client.get("/api/v1/admin/audit-logs", headers=headers)

    assert update.status_code == 200
    assert update.json()["is_active"] is False
    assert unavailable.status_code == 401
    assert any(item["action"] == "user.updated" for item in logs.json()["items"])


def test_admin_cannot_remove_own_access(client, db_session):
    admin = register(client, "self-protected-admin@example.com")
    promote(db_session, "self-protected-admin@example.com")
    response = client.patch(
        f"/api/v1/admin/users/{admin['user']['id']}",
        headers=auth_header(admin["access_token"]),
        json={"role": "learner"},
    )
    assert response.status_code == 409


def test_admin_can_review_and_delete_analysis(client, db_session):
    admin = register(client, "analysis-admin@example.com")
    learner = register(client, "analysis-owner@example.com")
    promote(db_session, "analysis-admin@example.com")
    admin_headers = auth_header(admin["access_token"])
    created = client.post(
        "/api/v1/analyses/writing",
        headers=auth_header(learner["access_token"]),
        json={"input_text": "I study English every day to improve my communication skills."},
    )
    assert created.status_code == 200

    listed = client.get("/api/v1/admin/analyses?type=writing", headers=admin_headers)
    deleted = client.delete(
        f"/api/v1/admin/analyses/{created.json()['id']}",
        headers=admin_headers,
    )
    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers)

    assert listed.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in listed.json()["items"])
    assert deleted.status_code == 200
    assert any(item["action"] == "analysis.deleted" for item in logs.json()["items"])
