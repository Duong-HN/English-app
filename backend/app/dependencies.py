import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .models import AuthSession, User, is_expired
from .security import decode_access_token_claims

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
            claims = decode_access_token_claims(token, settings)
            user_id = str(claims.get("sub")) if claims.get("sub") else None
            session_id = str(claims.get("sid")) if claims.get("sid") else None
            session = db.get(AuthSession, session_id) if session_id else None
            if (
                session is None
                or session.user_id != user_id
                or session.revoked_at is not None
                or is_expired(session.expires_at)
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or revoked access token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif settings.enable_dev_auth and settings.app_env.strip().lower() != "production" and dev_user:
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


def get_current_session_context(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> tuple[User, AuthSession]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token_claims(token, settings)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    user_id = str(claims.get("sub")) if claims.get("sub") else None
    session_id = str(claims.get("sid")) if claims.get("sid") else None
    session = db.get(AuthSession, session_id) if session_id else None
    user = db.get(User, user_id) if user_id else None
    if (
        user is None
        or not user.is_active
        or session is None
        or session.user_id != user.id
        or session.revoked_at is not None
        or is_expired(session.expires_at)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is unavailable")
    return user, session


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required",
        )
    return user


def require_learner(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"learner", "teacher"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learner or teacher access is required",
        )
    return user


def require_learner_only(user: User = Depends(get_current_user)) -> User:
    if user.role != "learner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Learner access is required",
        )
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access is required",
        )
    return user


def require_teacher_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"teacher", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or administrator access is required",
        )
    return user
