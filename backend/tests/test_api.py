from analysis_job_helpers import complete_legacy_analysis
from fastapi.testclient import TestClient


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Test Learner"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_and_readiness(client):
    health = client.get("/health")
    ready = client.get("/health/ready")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200


def test_register_and_get_profile(client):
    session = register(client, "profile@example.com")
    profile = client.get("/api/v1/auth/me", headers=auth_header(session["access_token"]))
    assert profile.status_code == 200
    assert profile.json()["email"] == "profile@example.com"
    assert "password_hash" not in profile.json()


def test_duplicate_registration_is_rejected(client):
    register(client, "duplicate@example.com")
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUPLICATE@example.com",
            "password": "safe-password-123",
            "display_name": "Other Learner",
        },
    )
    assert duplicate.status_code == 409


def test_login_and_invalid_password(client):
    register(client, "login@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "safe-password-123"},
    )
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "wrong-password"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]
    assert invalid.status_code == 401


def test_analysis_requires_authentication(client):
    response = client.post(
        "/api/v1/analyses/reading",
        json={"input_text": "The quick brown fox jumps over the lazy dog."},
    )
    assert response.status_code == 401


def test_legacy_analysis_alias_only_queues_work(client, monkeypatch):
    session = register(client, "analysis-async-alias@example.com")

    def unexpected_provider_call(_settings):
        raise AssertionError("legacy analysis endpoint must not invoke the AI provider")

    monkeypatch.setattr("app.worker.build_provider", unexpected_provider_call)
    response = client.post(
        "/api/v1/analyses/reading",
        headers=auth_header(session["access_token"]),
        json={"input_text": "The learner practices English every day."},
    )

    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert response.json()["analysis_id"] is None


def test_analysis_is_saved_and_deleted(client):
    session = register(client, "analysis@example.com")
    headers = auth_header(session["access_token"])
    created = complete_legacy_analysis(
        client,
        session["access_token"],
        "reading",
        {"input_text": "The learner practices English every day."},
    )
    assert created.status_code == 200
    assert created.json()["provider"] == "mock"
    assert created.json()["result"]["translation"]

    history = client.get("/api/v1/analyses", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1

    deleted = client.delete(f"/api/v1/analyses/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/api/v1/analyses", headers=headers).json()["total"] == 0


def test_histories_are_isolated_by_user(client):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    complete_legacy_analysis(
        client,
        first["access_token"],
        "writing",
        {"input_text": "I practice English because it helps my future career."},
    )
    second_history = client.get(
        "/api/v1/analyses",
        headers=auth_header(second["access_token"]),
    )
    assert second_history.status_code == 200
    assert second_history.json()["total"] == 0


def test_whitespace_input_is_rejected(client):
    session = register(client, "validation@example.com")
    response = client.post(
        "/api/v1/analyses/writing",
        json={"input_text": "   "},
        headers=auth_header(session["access_token"]),
    )
    assert response.status_code == 422


def test_analysis_validates_learning_context_before_calling_ai(client, monkeypatch):
    session = register(client, "analysis-context-first@example.com")

    def unexpected_provider_call(_settings):
        raise AssertionError("AI provider must not run for an unauthorized or missing learning path")

    monkeypatch.setattr("app.worker.build_provider", unexpected_provider_call)
    response = client.post(
        "/api/v1/analyses/writing",
        headers=auth_header(session["access_token"]),
        json={
            "input_text": "This otherwise valid response references a missing task.",
            "learning_path_id": "missing-path",
            "task_day": 1,
        },
    )
    assert response.status_code == 404
