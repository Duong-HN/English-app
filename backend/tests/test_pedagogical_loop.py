import asyncio

from analysis_job_helpers import complete_legacy_analysis
from fastapi.testclient import TestClient
from job_helpers import complete_legacy_learning_path
from sqlalchemy import select

from app.db import SessionLocal
from app.models import LearnerProfile, LearningPathJob, utc_now
from app.worker import process_learning_path_job


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Loop Learner"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def generate_path(client: TestClient, token: str) -> dict:
    return complete_legacy_learning_path(
        client,
        token,
        {"goal": "Improve English for work", "current_level": "A1", "minutes_per_day": 30},
    )


def allow_path_regeneration(db_session, user_id: str) -> None:
    profile = db_session.get(LearnerProfile, user_id)
    assert profile is not None
    profile.onboarding_completed_at = utc_now()
    db_session.commit()


def test_placement_test_sets_verified_level_for_future_paths(client, db_session):
    session = register(client, "placement-loop@example.com")
    headers = auth_header(session["access_token"])

    questions = client.get("/api/v1/placement-test", headers=headers)
    assert questions.status_code == 200
    assert questions.json()["total_questions"] == 20
    assert questions.json()["test_version"] == "2026-07-v1"
    assert {question["skill"] for question in questions.json()["questions"]} == {
        "grammar",
        "vocabulary",
        "reading",
    }
    assert all("answer" not in question for question in questions.json()["questions"])

    submitted = client.post(
        "/api/v1/placement-test/submit",
        headers=headers,
        json={
            "answers": {
                "q1": "b",
                "q2": "c",
                "q3": "b",
                "q4": "c",
                "q5": "b",
                "q6": "c",
                "q7": "a",
                "q8": "b",
                "q9": "c",
                "q10": "c",
                "q11": "b",
                "q12": "c",
                "q13": "a",
                "q14": "c",
                "q15": "b",
                "q16": "c",
                "q17": "b",
                "q18": "a",
                "q19": "c",
                "q20": "c",
            }
        },
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["score"] == 20
    assert submitted.json()["level"] == "C1"
    assert submitted.json()["skill_scores"]["reading"]["percentage"] == 100

    allow_path_regeneration(db_session, session["user"]["id"])
    path = generate_path(client, session["access_token"])
    assert path["current_level"] == "C1"
    assert path["level_source"] == "placement"
    assert path["placement_attempt_id"] == submitted.json()["id"]


def test_reading_vocabulary_is_saved_and_can_be_reviewed(client):
    session = register(client, "vocabulary-loop@example.com")
    headers = auth_header(session["access_token"])
    analysis = complete_legacy_analysis(
        client,
        session["access_token"],
        "reading",
        {"input_text": "The learner practices English every day."},
    )
    assert analysis.status_code == 200, analysis.text

    vocabulary = client.get("/api/v1/vocabulary", headers=headers)
    assert vocabulary.status_code == 200
    assert vocabulary.json()["total"] == 2
    item = vocabulary.json()["items"][0]
    updated = client.patch(
        f"/api/v1/vocabulary/{item['id']}",
        headers=headers,
        json={"status": "mastered"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "mastered"
    assert updated.json()["review_count"] == 1


def test_task_progress_and_analysis_context_close_the_feedback_loop(client, db_session):
    session = register(client, "progress-loop@example.com")
    headers = auth_header(session["access_token"])
    allow_path_regeneration(db_session, session["user"]["id"])
    path = generate_path(client, session["access_token"])

    completed = client.patch(
        f"/api/v1/learning-paths/{path['id']}/days/1",
        headers=headers,
        json={"completed": True, "note": "Finished the first task"},
    )
    assert completed.status_code == 200
    assert completed.json()["daily_progress"]["1"]["completed"] is True

    analysis = complete_legacy_analysis(
        client,
        session["access_token"],
        "writing",
        {
            "input_text": "I practice English every day to communicate better at work.",
            "learning_path_id": path["id"],
            "task_day": 2,
        },
    )
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()["learning_path_id"] == path["id"]
    assert analysis.json()["task_day"] == 2

    current = client.get("/api/v1/learning-paths/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["daily_progress"]["2"]["completed"] is True
    assert current.json()["daily_progress"]["2"]["analysis_id"] == analysis.json()["id"]

    adapted = client.post(f"/api/v1/learning-paths/{path['id']}/adapt", headers=headers)
    assert adapted.status_code == 202, adapted.text
    assert adapted.json()["operation"] == "adapt"
    with SessionLocal() as db:
        job = db.scalar(select(LearningPathJob).where(LearningPathJob.id == adapted.json()["id"]))
        assert job is not None
        job.status = "processing"
        job.attempt_count = 1
        job.started_at = utc_now()
        db.commit()
    asyncio.run(process_learning_path_job(adapted.json()["id"]))
    completed_job = client.get(
        f"/api/v1/learning-path-jobs/{adapted.json()['id']}",
        headers=headers,
    )
    assert completed_job.status_code == 200
    assert completed_job.json()["status"] == "succeeded"
    adapted_path = client.get(f"/api/v1/learning-paths/{path['id']}", headers=headers)
    assert adapted_path.status_code == 200
    assert adapted_path.json()["daily_progress"]["1"]["completed"] is True
    assert adapted_path.json()["daily_progress"]["2"]["completed"] is True
