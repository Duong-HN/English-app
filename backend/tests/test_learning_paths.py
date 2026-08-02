from analysis_job_helpers import complete_legacy_analysis
from fastapi.testclient import TestClient
from job_helpers import complete_legacy_learning_path
from sqlalchemy import func, select

from app.models import LearnerProfile, User, utc_now


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Path Learner"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def promote(db_session, email: str) -> None:
    user = db_session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None
    user.role = "admin"
    db_session.commit()


def allow_path_regeneration(db_session, user_id: str) -> None:
    profile = db_session.get(LearnerProfile, user_id)
    assert profile is not None
    profile.onboarding_completed_at = utc_now()
    db_session.commit()


def test_learning_path_requires_authentication_and_valid_input(client):
    missing_auth = client.post(
        "/api/v1/learning-paths/generate",
        json={"goal": "Improve communication", "current_level": "B1", "minutes_per_day": 30},
    )
    learner = register(client, "path-validation@example.com")
    invalid = client.post(
        "/api/v1/learning-paths/generate",
        headers=auth_header(learner["access_token"]),
        json={"goal": "Improve communication", "current_level": "B1", "minutes_per_day": 5},
    )

    assert missing_auth.status_code == 401
    assert invalid.status_code == 422


def test_generate_current_history_and_delete_personalized_path(client, db_session):
    learner = register(client, "path-owner@example.com")
    allow_path_regeneration(db_session, learner["user"]["id"])
    headers = auth_header(learner["access_token"])
    complete_legacy_analysis(
        client,
        learner["access_token"],
        "writing",
        {"input_text": "I want improve English because it help my future work."},
    )

    payload = complete_legacy_learning_path(
        client,
        learner["access_token"],
        {
            "goal": "Communicate confidently at work",
            "current_level": "B1",
            "minutes_per_day": 30,
        },
    )
    assert payload["provider"] == "mock"
    assert payload["current_level"] == "B1"
    assert payload["minutes_per_day"] == 30
    assert len(payload["plan"]["daily_tasks"]) == 7
    assert [task["day"] for task in payload["plan"]["daily_tasks"]] == list(range(1, 8))
    assert all(task["duration_minutes"] == 30 for task in payload["plan"]["daily_tasks"])
    assert payload["plan"]["personalization_notes"]

    current = client.get("/api/v1/learning-paths/current", headers=headers)
    history = client.get("/api/v1/learning-paths", headers=headers)
    profile = client.get("/api/v1/auth/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == payload["id"]
    assert history.json()["total"] == 1
    assert profile.json()["level"] == "B1"

    deleted = client.delete(f"/api/v1/learning-paths/{payload['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/api/v1/learning-paths/current", headers=headers).status_code == 404


def test_learning_paths_are_isolated_and_administrator_can_moderate(client, db_session):
    owner = register(client, "path-admin-owner@example.com")
    stranger = register(client, "path-stranger@example.com")
    admin = register(client, "path-admin@example.com")
    promote(db_session, "path-admin@example.com")
    allow_path_regeneration(db_session, owner["user"]["id"])

    generated = complete_legacy_learning_path(
        client,
        owner["access_token"],
        {"goal": "Prepare for an English interview", "current_level": "A2", "minutes_per_day": 20},
    )
    assert (
        client.get(
            "/api/v1/learning-paths/current",
            headers=auth_header(stranger["access_token"]),
        ).status_code
        == 404
    )

    admin_headers = auth_header(admin["access_token"])
    listed = client.get("/api/v1/admin/learning-paths?q=interview", headers=admin_headers)
    assert listed.status_code == 200
    assert any(item["id"] == generated["id"] for item in listed.json()["items"])

    deleted = client.delete(
        f"/api/v1/admin/learning-paths/{generated['id']}",
        headers=admin_headers,
    )
    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert deleted.status_code == 200
    assert any(item["action"] == "learning_path.deleted" for item in logs.json()["items"])
