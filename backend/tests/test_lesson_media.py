from io import BytesIO

from analysis_job_helpers import complete_legacy_analysis
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.models import LessonMedia, User


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


def first_lesson(client: TestClient, session: dict, skill: str | None = None) -> dict:
    response = client.get("/api/v1/content/courses", headers=headers(session))
    assert response.status_code == 200, response.text
    for course in response.json()["items"]:
        for unit in course["units"]:
            for lesson in unit["lessons"]:
                if skill is None or lesson["skill"] == skill:
                    return lesson
    raise AssertionError("No lesson found")


def test_admin_uploads_media_and_learner_streams_it(client, db_session, tmp_path):
    get_settings().media_storage_dir = str(tmp_path)
    admin = register(client, "media-admin@example.com", "Media Admin")
    learner = register(client, "media-learner@example.com", "Media Learner")
    set_role(db_session, "media-admin@example.com", "admin")
    lesson = first_lesson(client, learner, skill="listening")

    upload = client.post(
        f"/api/v1/content/admin/lessons/{lesson['id']}/media",
        headers=headers(admin),
        data={
            "media_type": "audio",
            "title": "Listening practice",
            "transcript": "This is a real lesson transcript.",
            "duration_seconds": "42",
            "sort_order": "0",
            "is_published": "true",
        },
        files={"file": ("practice.mp3", BytesIO(b"fake-audio-bytes"), "audio/mpeg")},
    )
    assert upload.status_code == 201, upload.text
    media = upload.json()
    assert media["media_type"] == "audio"
    assert media["file_size_bytes"] == len(b"fake-audio-bytes")
    assert media["transcript"] == "This is a real lesson transcript."

    learner_lesson = client.get(
        f"/api/v1/content/lessons/{lesson['id']}",
        headers=headers(learner),
    )
    assert learner_lesson.status_code == 200, learner_lesson.text
    assert learner_lesson.json()["media"][0]["id"] == media["id"]
    assert learner_lesson.json()["media_url"] == media["media_url"]

    stream = client.get(media["media_url"], headers=headers(learner))
    assert stream.status_code == 200, stream.text
    assert stream.content == b"fake-audio-bytes"
    assert stream.headers["content-type"].startswith("audio/mpeg")

    partial_stream = client.get(
        media["media_url"],
        headers={**headers(learner), "Range": "bytes=5-9"},
    )
    assert partial_stream.status_code == 206
    assert partial_stream.content == b"audio"
    assert partial_stream.headers["content-range"] == "bytes 5-9/16"

    progress = client.patch(
        f"/api/v1/content/lessons/{lesson['id']}/media-progress",
        headers=headers(learner),
        json={
            "media_id": media["id"],
            "position_seconds": 34,
            "completed": True,
        },
    )
    assert progress.status_code == 200, progress.text
    assert progress.json()["media_progress"][media["id"]]["position_seconds"] == 34
    assert progress.json()["media_progress"][media["id"]]["completed"] is True

    courses = client.get("/api/v1/content/courses", headers=headers(learner))
    listening_summary = next(
        item
        for course in courses.json()["items"]
        for unit in course["units"]
        for item in unit["lessons"]
        if item["id"] == lesson["id"]
    )
    assert listening_summary["media_count"] == 1
    assert db_session.scalar(select(LessonMedia).where(LessonMedia.id == media["id"])) is not None


def test_lesson_context_is_sent_to_ai_and_persisted(client, db_session):
    learner = register(client, "media-context@example.com", "Media Context")
    lesson = first_lesson(client, learner, skill="reading")

    response = complete_legacy_analysis(
        client,
        learner["access_token"],
        "reading",
        {
            "input_text": "The learner submitted a short answer for this lesson.",
            "lesson_id": lesson["id"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["lesson_id"] == lesson["id"]
    assert lesson["title"] in response.json()["result"]["summary"]


def test_learner_cannot_manage_global_lesson_media(client):
    learner = register(client, "media-forbidden@example.com", "Media Forbidden")
    lesson = first_lesson(client, learner)
    response = client.post(
        f"/api/v1/content/admin/lessons/{lesson['id']}/media",
        headers=headers(learner),
        data={"media_type": "audio", "title": "Not allowed"},
        files={"file": ("blocked.mp3", BytesIO(b"nope"), "audio/mpeg")},
    )
    assert response.status_code == 403
