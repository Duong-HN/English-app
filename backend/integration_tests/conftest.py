import os
import sys
from pathlib import Path

import pytest

postgres_url = os.getenv("POSTGRES_TEST_DATABASE_URL")
if postgres_url:
    os.environ.update(
        {
            "DATABASE_URL": postgres_url,
            "APP_ENV": "test",
            "AUTO_CREATE_SCHEMA": "false",
            "AI_PROVIDER": "mock",
            "ENABLE_DEV_AUTH": "false",
            "JWT_SECRET": "postgres-integration-secret-that-is-long-enough",
        }
    )
    sys.path.insert(0, str(Path(__file__).parents[1]))

    from fastapi.testclient import TestClient  # noqa: E402

    from app.main import app  # noqa: E402

    @pytest.fixture(scope="session")
    def client():
        with TestClient(app) as test_client:
            yield test_client
