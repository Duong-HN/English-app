from datetime import timedelta
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..dependencies import get_current_session_context, get_current_user, require_admin
from ..models import AuthSession, LearnerProfile, LearningSpace, User, is_expired, utc_now
from ..schemas import (
    LoginRequest,
    MfaCodeRequest,
    MfaSetupResponse,
    MfaStatusResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from ..security import (
    create_access_token,
    create_refresh_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_totp_secret,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_totp,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _issue_tokens(user: User, db: Session, settings: Settings, request: Request) -> TokenResponse:
    refresh_token = create_refresh_token()
    session = AuthSession(
        id=str(uuid4()),
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_days),
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, settings, session.id),
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = request.email.lower()
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        email=email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
    )
    user.learner_profile = LearnerProfile()
    user.learning_spaces.append(
        LearningSpace(
            kind="self",
            name="Tự học",
        )
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc
    db.refresh(user)
    return _issue_tokens(user, db, settings, http_request)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    email = request.email.lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not user.is_active or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role == "admin" and user.mfa_enabled:
        if not request.mfa_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA code is required")
        try:
            valid_mfa = verify_totp(
                decrypt_mfa_secret(user.mfa_secret_encrypted or "", settings),
                request.mfa_code,
            )
        except ValueError:
            valid_mfa = False
        if not valid_mfa:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
    user.last_login_at = utc_now()
    user.updated_at = utc_now()
    db.commit()
    db.refresh(user)
    return _issue_tokens(user, db, settings, http_request)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshTokenRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == hash_refresh_token(request.refresh_token))
    )
    now = utc_now()
    if session is None or session.revoked_at is not None or is_expired(session.expires_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is unavailable")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable")
    rotated_refresh = create_refresh_token()
    session.refresh_token_hash = hash_refresh_token(rotated_refresh)
    session.last_used_at = now
    session.user_agent = (http_request.headers.get("user-agent") or "")[:500] or session.user_agent
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, settings, session.id),
        refresh_token=rotated_refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    context: tuple[User, AuthSession] = Depends(get_current_session_context),
    db: Session = Depends(get_db),
):
    _, session = context
    session.revoked_at = utc_now()
    db.commit()
    return None


@router.get("/mfa/status", response_model=MfaStatusResponse)
def mfa_status(user: User = Depends(require_admin)):
    return MfaStatusResponse(enabled=user.mfa_enabled)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is already enabled")
    secret = generate_totp_secret()
    user.mfa_secret_encrypted = encrypt_mfa_secret(secret, settings)
    db.commit()
    label = quote(f"LearnMate:{user.email}")
    issuer = quote("LearnMate")
    return MfaSetupResponse(
        secret=secret,
        otpauth_uri=f"otpauth://totp/{label}?secret={secret}&issuer={issuer}",
    )


@router.post("/mfa/enable", response_model=MfaStatusResponse)
def mfa_enable(
    request: MfaCodeRequest,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not user.mfa_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA setup is required first")
    if not verify_totp(decrypt_mfa_secret(user.mfa_secret_encrypted, settings), request.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")
    user.mfa_enabled = True
    db.commit()
    return MfaStatusResponse(enabled=True)


@router.post("/mfa/disable", response_model=MfaStatusResponse)
def mfa_disable(
    request: MfaCodeRequest,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not user.mfa_enabled or not user.mfa_secret_encrypted:
        return MfaStatusResponse(enabled=False)
    if not verify_totp(decrypt_mfa_secret(user.mfa_secret_encrypted, settings), request.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code")
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    db.commit()
    return MfaStatusResponse(enabled=False)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)
