import os
from pathlib import Path
import sys

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_learnmate.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "development"
Path("test_learnmate.db").unlink(missing_ok=True)
sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_reading_analysis_is_saved(client):
    response = client.post(
        "/api/v1/analyses/reading",
        json={"input_text": "The quick brown fox jumps over the lazy dog."},
        headers={"X-Dev-User": "test-user"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["result"]["translation"]

    history = client.get("/api/v1/analyses", headers={"X-Dev-User": "test-user"})
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1


def test_empty_input_is_rejected(client):
    response = client.post("/api/v1/analyses/writing", json={"input_text": ""})
    assert response.status_code == 422
