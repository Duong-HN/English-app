from fastapi.testclient import TestClient

from app.content_catalog import recommended_course_code


def register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "safe-password-123",
            "display_name": "A2 B1 Learner",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a2_b1_pack_is_the_recommended_course():
    assert recommended_course_code("A2") == "core-b1"
    assert recommended_course_code("B1") == "core-b1"


def test_a2_b1_pack_exposes_six_structured_lessons(client):
    session = register(client, "a2b1-pack-detail@example.com")
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    response = client.get("/api/v1/content/courses?level=B1", headers=headers)

    assert response.status_code == 200, response.text
    courses = response.json()["items"]
    assert len(courses) == 1
    course = courses[0]
    assert course["code"] == "core-b1"
    assert course["title"] == "English A2 → B1 · Everyday Communication"
    assert len(course["units"]) == 2
    assert all(len(unit["lessons"]) == 3 for unit in course["units"])

    lesson_id = course["units"][0]["lessons"][0]["id"]
    detail = client.get(f"/api/v1/content/lessons/{lesson_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert len(payload["content_pack"]["objectives"]) == 3
    assert payload["content_pack"]["vocabulary"]
    assert payload["content_pack"]["reading"]["questions"]
    assert payload["content_pack"]["answer_key"]
    assert payload["source_attribution"].startswith("Original LearnMate")
    assert payload["license_name"]


def test_a2_b1_pack_has_three_original_video_plans(client):
    session = register(client, "a2b1-pack-media@example.com")
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    response = client.get("/api/v1/content/courses?level=B1", headers=headers)
    course = response.json()["items"][0]
    lesson_ids = [lesson["id"] for unit in course["units"] for lesson in unit["lessons"]]

    plans = []
    for lesson_id in lesson_ids:
        detail = client.get(f"/api/v1/content/lessons/{lesson_id}", headers=headers)
        plans.append(detail.json()["content_pack"].get("media_plan"))

    video_plans = [plan for plan in plans if plan]
    assert len(video_plans) == 3
    assert all(plan["media_type"] == "video" for plan in video_plans)
    assert all(plan["source"].startswith("Original project") for plan in video_plans)
