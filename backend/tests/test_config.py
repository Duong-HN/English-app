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
