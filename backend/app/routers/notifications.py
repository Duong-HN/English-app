from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Notification, PushDevice, User, utc_now
from ..schemas import (
    NotificationListResponse,
    NotificationResponse,
    PushDeviceRegisterRequest,
    PushDeviceResponse,
    PushDeviceUnregisterRequest,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _as_utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        kind=notification.kind,
        title=notification.title,
        body=notification.body,
        data=notification.data or {},
        read_at=_as_utc(notification.read_at) if notification.read_at else None,
        created_at=_as_utc(notification.created_at),
    )


def _device_response(device: PushDevice) -> PushDeviceResponse:
    return PushDeviceResponse(
        id=device.id,
        platform=device.platform,
        enabled=device.enabled,
        last_seen_at=_as_utc(device.last_seen_at),
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notifications = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    ).all()
    unread_count = (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user.id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    return NotificationListResponse(
        items=[_response(item) for item in notifications],
        unread_count=unread_count,
        total=len(notifications),
    )


@router.post("/devices", response_model=PushDeviceResponse)
def register_push_device(
    payload: PushDeviceRegisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Register or refresh one FCM token for the signed-in user."""

    device = db.scalar(select(PushDevice).where(PushDevice.token == payload.token))
    if device is None:
        device = PushDevice(token=payload.token)
        db.add(device)
    # A token can only belong to one account. Re-registering after account
    # switching moves it to the current user instead of leaking notifications.
    device.user_id = user.id
    device.platform = payload.platform
    device.app_version = payload.app_version
    device.enabled = True
    device.last_seen_at = utc_now()
    device.updated_at = utc_now()
    db.commit()
    db.refresh(device)
    return _device_response(device)


@router.post("/devices/unregister", status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_device(
    payload: PushDeviceUnregisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = db.scalar(
        select(PushDevice).where(
            PushDevice.token == payload.token,
            PushDevice.user_id == user.id,
        )
    )
    if device is not None:
        device.enabled = False
        device.updated_at = utc_now()
        db.commit()


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.read_at = notification.read_at or utc_now()
    db.commit()
    db.refresh(notification)
    return _response(notification)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read_at.is_(None),
    ).update({Notification.read_at: utc_now()}, synchronize_session=False)
    db.commit()
