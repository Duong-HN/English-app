import os
import sys
from pathlib import Path

import pytest

test_database = Path(__file__).with_name("learnmate_test.db")
test_database.unlink(missing_ok=True)
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{test_database.as_posix()}",
        "AI_PROVIDER": "mock",
        "APP_ENV": "test",
        "AUTO_CREATE_SCHEMA": "true",
        "ENABLE_DEV_AUTH": "false",
        "JWT_SECRET": "test-secret-that-is-long-enough-for-automated-tests",
    }
)
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session(client):
    with SessionLocal() as session:
        yield session
