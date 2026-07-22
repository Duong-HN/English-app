import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .models import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    dev_user: str | None = Header(default=None, alias="X-Dev-User"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    user_id: str | None = None
    if token:
        try:
            user_id = decode_access_token(token, settings)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif settings.enable_dev_auth and settings.app_env != "production" and dev_user:
        user_id = dev_user
        user = db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                email=f"{user_id}@example.local",
                display_name="Development learner",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required",
        )
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access is required",
        )
    return user


def require_learner(user: User = Depends(get_current_user)) -> User:
    if user.role != "learner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learner access is required",
        )
    return user
