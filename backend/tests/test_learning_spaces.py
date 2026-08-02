from analysis_job_helpers import complete_legacy_analysis
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import Analysis, User


def register(client: TestClient, email: str, display_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(session: dict, **extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {session['access_token']}",
        **extra,
    }


def set_role(db_session, email: str, role: str) -> None:
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.role = role
    db_session.commit()


def test_onboarding_can_choose_self_or_join_class(client, db_session):
    teacher = register(client, "spaces-teacher@example.com", "Space Teacher")
    learner = register(client, "spaces-learner@example.com", "Space Learner")
    set_role(db_session, "spaces-teacher@example.com", "teacher")

    initial = client.get("/api/v1/onboarding", headers=headers(learner))
    assert initial.status_code == 200
    assert initial.json()["status"] == "needs_mode"
    assert initial.json()["space"]["kind"] == "self"

    selected = client.patch(
        "/api/v1/onboarding/mode",
        headers=headers(learner),
        json={"kind": "self"},
    )
    assert selected.status_code == 200
    assert selected.json()["status"] == "needs_goal"

    classroom = client.post(
        "/api/v1/classes",
        headers=headers(teacher),
        json={"name": "Isolated Space Class"},
    )
    assert classroom.status_code == 201, classroom.text
    joined = client.post(
        "/api/v1/learning-spaces/join",
        headers=headers(learner),
        json={"invite_code": classroom.json()["invite_code"]},
    )
    assert joined.status_code == 201, joined.text
    assert joined.json()["kind"] == "class"
    class_space_id = joined.json()["id"]

    spaces = client.get("/api/v1/learning-spaces", headers=headers(learner))
    assert spaces.status_code == 200
    assert {item["kind"] for item in spaces.json()["items"]} == {"self", "class"}

    class_onboarding = client.get(
        "/api/v1/onboarding",
        headers=headers(learner, **{"X-Learning-Space-ID": class_space_id}),
    )
    assert class_onboarding.status_code == 200
    assert class_onboarding.json()["status"] == "class_ready"
    assert class_onboarding.json()["goal"] is None
    assert class_onboarding.json()["learning_path"] is None


def test_curriculum_and_analysis_progress_are_scoped_to_space(client, db_session):
    teacher = register(client, "curriculum-teacher@example.com", "Curriculum Teacher")
    learner = register(client, "curriculum-learner@example.com", "Curriculum Learner")
    set_role(db_session, "curriculum-teacher@example.com", "teacher")
    classroom = client.post(
        "/api/v1/classes",
        headers=headers(teacher),
        json={"name": "Curriculum Isolation"},
    )
    joined = client.post(
        "/api/v1/learning-spaces/join",
        headers=headers(learner),
        json={"invite_code": classroom.json()["invite_code"]},
    )
    class_space_id = joined.json()["id"]
    class_headers = headers(learner, **{"X-Learning-Space-ID": class_space_id})

    courses = client.get("/api/v1/content/courses", headers=headers(learner))
    assert courses.status_code == 200, courses.text
    assert courses.json()["total"] == 9
    ielts = next(item for item in courses.json()["items"] if item["code"] == "ielts-band-5-6")
    assert ielts["band_min"] == 5.0
    assert ielts["band_max"] == 6.0
    assert len(ielts["units"]) == 2
    assert all(len(unit["lessons"]) == 2 for unit in ielts["units"])
    assert {item["code"] for item in courses.json()["items"] if item["kind"] == "ielts"} == {
        "ielts-band-4-5",
        "ielts-band-5-6",
        "ielts-band-6-7",
        "ielts-band-7-8",
    }

    lesson_id = ielts["units"][0]["lessons"][0]["id"]
    completed = client.patch(
        f"/api/v1/content/lessons/{lesson_id}/progress",
        headers=headers(learner),
        json={"status": "completed", "score": 8.5},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["progress_status"] == "completed"
    class_curriculum = client.get("/api/v1/content/courses", headers=class_headers)
    assert class_curriculum.status_code == 409

    self_analysis = complete_legacy_analysis(
        client,
        learner["access_token"],
        "reading",
        {"input_text": "A short self-study reading sample."},
    )
    class_analysis = complete_legacy_analysis(
        client,
        learner["access_token"],
        "reading",
        {"input_text": "A short class reading sample."},
        extra_headers=class_headers,
    )
    assert self_analysis.status_code == 200, self_analysis.text
    assert class_analysis.status_code == 200, class_analysis.text

    self_history = client.get("/api/v1/analyses", headers=headers(learner))
    class_history = client.get("/api/v1/analyses", headers=class_headers)
    assert self_history.json()["total"] == 1
    assert class_history.json()["total"] == 1
    assert self_history.json()["items"][0]["id"] == self_analysis.json()["id"]
    assert class_history.json()["items"][0]["id"] == class_analysis.json()["id"]
    assert (
        db_session.scalar(
            select(func.count()).select_from(Analysis).where(Analysis.user_id == learner["user"]["id"])
        )
        == 2
    )
