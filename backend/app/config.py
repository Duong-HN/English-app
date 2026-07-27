from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LearnMate AI API"
    app_version: str = "0.7.0"
    app_env: str = "development"
    database_url: str = "sqlite:///./learnmate.db"
    auto_create_schema: bool = True

    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    enable_dev_auth: bool = True

    ai_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    ai_timeout_seconds: float = 45

    media_storage_dir: str = "./media"
    media_max_size_mb: int = 100
    media_public_base_url: str | None = None

    allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.app_env == "production":
            if self.jwt_secret == "development-only-change-me" or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be a random value of at least 32 characters in production")
            if self.enable_dev_auth:
                raise ValueError("ENABLE_DEV_AUTH must be false in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
