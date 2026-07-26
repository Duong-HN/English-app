from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import LearnerProfile, LearningPath
from app.placement import PLACEMENT_QUESTIONS, score_answers


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": "Onboarding Learner"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def correct_answers() -> dict[str, str]:
    return {question.id: question.answer for question in PLACEMENT_QUESTIONS}


def test_placement_requires_all_20_questions_and_scores_each_skill(client):
    session = register(client, "placement-20@example.com")
    headers = auth_header(session["access_token"])
    test = client.get("/api/v1/placement-test", headers=headers)

    assert test.status_code == 200
    assert test.json()["total_questions"] == 20
    assert len(test.json()["questions"]) == 20
    assert all("answer" not in question and "level" not in question for question in test.json()["questions"])

    incomplete = correct_answers()
    incomplete.pop("q20")
    rejected = client.post(
        "/api/v1/placement-test/submit",
        headers=headers,
        json={"answers": incomplete},
    )
    assert rejected.status_code == 422

    submitted = client.post(
        "/api/v1/placement-test/submit",
        headers=headers,
        json={"answers": correct_answers()},
    )
    assert submitted.status_code == 201, submitted.text
    assert submitted.json()["score"] == 20
    assert submitted.json()["level"] == "C1"
    assert submitted.json()["test_version"] == "2026-07-v1"
    assert all(score["percentage"] == 100 for score in submitted.json()["skill_scores"].values())


def test_placement_level_thresholds_cover_a1_through_c1():
    answers = {question.id: "?" for question in PLACEMENT_QUESTIONS}
    for correct_count, expected_level in ((4, "A1"), (5, "A2"), (9, "B1"), (13, "B2"), (17, "C1")):
        candidate = dict(answers)
        for question in PLACEMENT_QUESTIONS[:correct_count]:
            candidate[question.id] = question.answer
        score, level, skill_scores = score_answers(candidate)
        assert score == correct_count
        assert level == expected_level
        assert set(skill_scores) == {"grammar", "vocabulary", "reading"}


def test_onboarding_resumes_and_complete_is_idempotent(client, db_session):
    session = register(client, "onboarding-resume@example.com")
    headers = auth_header(session["access_token"])

    initial = client.get("/api/v1/onboarding", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["status"] == "needs_goal"

    goal = client.patch(
        "/api/v1/onboarding/preferences",
        headers=headers,
        json={"goal": "work"},
    )
    assert goal.status_code == 200
    assert goal.json()["status"] == "needs_daily_time"
    resumed = client.get("/api/v1/onboarding", headers=headers)
    assert resumed.json()["goal"] == "work"
    assert resumed.json()["status"] == "needs_daily_time"

    daily_time = client.patch(
        "/api/v1/onboarding/preferences",
        headers=headers,
        json={"daily_minutes": 30},
    )
    assert daily_time.status_code == 200
    assert daily_time.json()["status"] == "needs_placement"

    too_early = client.post("/api/v1/onboarding/complete", headers=headers)
    assert too_early.status_code == 409

    placement = client.post(
        "/api/v1/placement-test/submit",
        headers=headers,
        json={"answers": correct_answers()},
    )
    assert placement.status_code == 201
    ready = client.get("/api/v1/onboarding", headers=headers)
    assert ready.json()["status"] == "needs_learning_path"

    completed = client.post("/api/v1/onboarding/complete", headers=headers)
    assert completed.status_code == 200, completed.text
    payload = completed.json()
    assert payload["status"] == "completed"
    assert payload["goal"] == "work"
    assert payload["daily_minutes"] == 30
    assert payload["placement_result"]["id"] == placement.json()["id"]
    assert payload["learning_path"]["current_level"] == "C1"
    assert payload["learning_path"]["goal"] == "Improve English for work and career"
    assert len(payload["learning_path"]["plan"]["daily_tasks"]) == 7

    repeated = client.post("/api/v1/onboarding/complete", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["learning_path"]["id"] == payload["learning_path"]["id"]
    path_count = db_session.scalar(
        select(func.count()).select_from(LearningPath).where(LearningPath.user_id == session["user"]["id"])
    )
    assert path_count == 1


def test_existing_learning_path_is_safely_backfilled_as_completed(client, db_session):
    session = register(client, "onboarding-legacy@example.com")
    headers = auth_header(session["access_token"])
    blocked = client.post(
        "/api/v1/learning-paths/generate",
        headers=headers,
        json={
            "goal": "Prepare for an English job interview",
            "current_level": "B1",
            "minutes_per_day": 20,
        },
    )
    assert blocked.status_code == 409

    profile = db_session.get(LearnerProfile, session["user"]["id"])
    assert profile is not None
    db_session.delete(profile)
    db_session.commit()
    generated = client.post(
        "/api/v1/learning-paths/generate",
        headers=headers,
        json={
            "goal": "Prepare for an English job interview",
            "current_level": "B1",
            "minutes_per_day": 20,
        },
    )
    assert generated.status_code == 201

    onboarding = client.get("/api/v1/onboarding", headers=headers)
    assert onboarding.status_code == 200
    assert onboarding.json()["status"] == "completed"
    assert onboarding.json()["goal"] == "work"
    assert onboarding.json()["daily_minutes"] == 20
    assert onboarding.json()["placement_result"] is None

    db_session.expire_all()
    backfilled_profile = db_session.get(LearnerProfile, session["user"]["id"])
    assert backfilled_profile is not None
    assert backfilled_profile.onboarding_completed_at is not None
