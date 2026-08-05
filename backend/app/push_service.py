"""Best-effort Firebase Cloud Messaging delivery.

In-app notifications remain the source of truth. Push delivery is optional and
must never make a group action fail when Firebase is not configured or is
temporarily unavailable.
"""

import json
import time
from pathlib import Path
from typing import Any

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .models import Notification, PushDevice

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_cached_access_token: str | None = None
_cached_access_token_expires_at = 0.0


def _load_service_account(settings: Settings) -> dict[str, Any]:
    raw = settings.fcm_service_account_json
    if raw:
        return json.loads(raw)
    if settings.fcm_service_account_file:
        return json.loads(Path(settings.fcm_service_account_file).read_text(encoding="utf-8"))
    raise RuntimeError("FCM service account credentials are not configured")


def _get_access_token(client: httpx.Client, settings: Settings) -> str:
    global _cached_access_token, _cached_access_token_expires_at

    now = time.time()
    if _cached_access_token and _cached_access_token_expires_at > now + 60:
        return _cached_access_token

    service_account = _load_service_account(settings)
    token_uri = service_account.get("token_uri", "https://oauth2.googleapis.com/token")
    issued_at = int(now)
    assertion = jwt.encode(
        {
            "iss": service_account["client_email"],
            "scope": FCM_SCOPE,
            "aud": token_uri,
            "iat": issued_at,
            "exp": issued_at + 3600,
        },
        service_account["private_key"],
        algorithm="RS256",
    )
    response = client.post(
        token_uri,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
    )
    response.raise_for_status()
    payload = response.json()
    _cached_access_token = payload["access_token"]
    _cached_access_token_expires_at = now + int(payload.get("expires_in", 3600))
    return _cached_access_token


def _stringify_data(data: dict | None) -> dict[str, str]:
    result = {"notification_id": "", "kind": ""}
    for key, value in (data or {}).items():
        if isinstance(value, str):
            result[str(key)] = value
        else:
            result[str(key)] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return result


def _send_to_device(
    client: httpx.Client,
    device: PushDevice,
    notification: Notification,
    settings: Settings,
) -> tuple[bool, str | None]:
    access_token = _get_access_token(client, settings)
    url = f"https://fcm.googleapis.com/v1/projects/{settings.fcm_project_id}/messages:send"
    data = _stringify_data(notification.data)
    data["notification_id"] = notification.id
    data["kind"] = notification.kind
    response = client.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; UTF-8",
        },
        json={
            "message": {
                "token": device.token,
                "notification": {
                    "title": notification.title,
                    "body": notification.body,
                },
                "data": data,
            }
        },
    )
    if response.is_success:
        return True, None

    reason = response.text[:500]
    # FCM returns UNREGISTERED/INVALID_ARGUMENT for tokens that should no
    # longer be retried. Disable them until the client registers a new token.
    if response.status_code == 400 and any(
        marker in response.text for marker in ("UNREGISTERED", "INVALID_ARGUMENT")
    ):
        device.enabled = False
    return False, reason


def dispatch_push(
    db: Session,
    notification: Notification,
    *,
    settings: Settings | None = None,
) -> None:
    """Send a notification to the user's active devices without raising.

    This is intentionally synchronous for the current prototype. The helper
    is isolated so it can move behind a queue/outbox worker once push volume
    warrants it.
    """

    settings = settings or get_settings()
    devices = db.scalars(
        select(PushDevice).where(
            PushDevice.user_id == notification.user_id,
            PushDevice.enabled.is_(True),
        )
    ).all()
    if not devices:
        notification.push_status = "skipped"
        return
    if settings.push_provider.lower() != "fcm":
        notification.push_status = "skipped"
        notification.push_error = "PUSH_PROVIDER is not configured"
        return

    sent = 0
    errors: list[str] = []
    try:
        with httpx.Client(timeout=settings.push_timeout_seconds) as client:
            for device in devices:
                try:
                    delivered, error = _send_to_device(client, device, notification, settings)
                    if delivered:
                        sent += 1
                    elif error:
                        errors.append(error)
                except Exception as exc:  # pragma: no cover - depends on Firebase/network
                    errors.append(str(exc)[:500])
    except Exception as exc:  # pragma: no cover - depends on Firebase/network
        errors.append(str(exc)[:500])

    if sent and not errors:
        notification.push_status = "sent"
        notification.push_error = None
    elif sent:
        notification.push_status = "partial"
        notification.push_error = "; ".join(errors)[:1000]
    else:
        notification.push_status = "failed"
        notification.push_error = "; ".join(errors)[:1000] or "FCM delivery failed"
