import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_weak_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            app_env="production",
            jwt_secret="too-short",
            enable_dev_auth=False,
        )


def test_production_rejects_development_authentication():
    with pytest.raises(ValidationError, match="ENABLE_DEV_AUTH"):
        Settings(
            app_env="production",
            jwt_secret="a-production-secret-with-at-least-32-characters",
            enable_dev_auth=True,
        )


def test_production_accepts_explicit_safe_configuration():
    settings = Settings(
        app_env="production",
        database_url="postgresql://learnmate:secret@example.com/learnmate",
        auto_create_schema=False,
        jwt_secret="a-production-secret-with-at-least-32-characters",
        enable_dev_auth=False,
        ai_provider="gemini",
        gemini_api_key="configured-provider-key",
        allowed_origins="https://learnmate.example.com",
        media_public_base_url="https://media.learnmate.example.com",
        rate_limit_backend="redis",
        redis_url="redis://redis.internal:6379/0",
        mfa_encryption_key="a-separate-mfa-encryption-key-with-32-chars",
    )

    assert settings.app_env == "production"
