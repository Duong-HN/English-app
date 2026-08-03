import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import User
from app.security import _totp_code


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Security User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_refresh_rotates_token_and_logout_revokes_access(client):
    session = register(client, f"refresh-{uuid4().hex}@example.com")
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": session["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["refresh_token"] != session["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": session["refresh_token"]},
    )
    assert reused.status_code == 401

    logged_out = client.post(
        "/api/v1/auth/logout",
        headers=auth_header(refreshed.json()["access_token"]),
    )
    assert logged_out.status_code == 204
    revoked_access = client.get(
        "/api/v1/auth/me",
        headers=auth_header(refreshed.json()["access_token"]),
    )
    assert revoked_access.status_code == 401


def test_admin_mfa_setup_enable_and_login_challenge(client, db_session):
    email = f"mfa-{uuid4().hex}@example.com"
    initial = register(client, email)
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = "admin"
    db_session.commit()

    setup = client.post("/api/v1/auth/mfa/setup", headers=auth_header(initial["access_token"]))
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    code = _totp_code(secret, int(time.time()))
    enabled = client.post(
        "/api/v1/auth/mfa/enable",
        headers=auth_header(initial["access_token"]),
        json={"code": code},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "safe-password-123"},
    )
    assert blocked.status_code == 401
    authenticated = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "safe-password-123", "mfa_code": code},
    )
    assert authenticated.status_code == 200, authenticated.text
