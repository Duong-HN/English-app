from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.models import Assignment, AssignmentSubmission, Classroom, User


def register(client: TestClient, email: str, display_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def deadline() -> str:
    return (datetime.now(UTC) + timedelta(days=2)).isoformat()


def test_users_create_group_collaborate_peer_review_and_rank(client, db_session):
    owner = register(client, "group-owner@example.com", "Group Owner")
    member = register(client, "group-member@example.com", "Group Member")
    owner_user = db_session.get(User, owner["user"]["id"])
    member_user = db_session.get(User, member["user"]["id"])
    assert owner_user is not None and member_user is not None
    owner_user.level = "B1"
    member_user.level = "B1"
    db_session.commit()

    created = client.post(
        "/api/v1/study-groups",
        headers=auth(owner["access_token"]),
        json={"name": "B1 Speaking Circle", "description": "Học cùng nhau", "level": "B1"},
    )
    assert created.status_code == 201, created.text
    group = created.json()
    assert group["is_owner"] is True
    assert group["member_count"] == 1
    assert group["invite_code"]
    assert group["invite_link"].startswith("learnmate://study-groups/join?token=")

    joined = client.post(
        "/api/v1/study-groups/join",
        headers=auth(member["access_token"]),
        json={"invite_code": group["invite_code"].lower()},
    )
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "pending"
    invitation_id = joined.json()["invitation"]["id"]

    notifications = client.get(
        "/api/v1/notifications",
        headers=auth(owner["access_token"]),
    )
    assert notifications.status_code == 200, notifications.text
    assert notifications.json()["unread_count"] == 1

    pending = client.get(
        "/api/v1/study-groups/invitations",
        headers=auth(owner["access_token"]),
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["total"] == 1

    approved = client.post(
        f"/api/v1/study-groups/invitations/{invitation_id}/approve",
        headers=auth(owner["access_token"]),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["member_count"] == 2

    assignment = client.post(
        f"/api/v1/study-groups/{group['id']}/assignments",
        headers=auth(owner["access_token"]),
        json={
            "title": "Describe a memorable trip",
            "skill": "writing",
            "content": "Write a short paragraph.",
            "estimated_minutes": 20,
            "due_at": deadline(),
            "review_deadline": (datetime.now(UTC) + timedelta(days=4)).isoformat(),
        },
    )
    assert assignment.status_code == 201, assignment.text
    assignment_id = assignment.json()["id"]

    submitted = client.post(
        f"/api/v1/assignments/{assignment_id}/submit",
        headers=auth(member["access_token"]),
        json={"input_text": "I travelled to Da Nang last summer with my family."},
    )
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["id"]

    queue = client.get(
        f"/api/v1/study-groups/{group['id']}/assignments/{assignment_id}/peer-reviews",
        headers=auth(owner["access_token"]),
    )
    assert queue.status_code == 200, queue.text
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["submission_id"] == submission_id

    review = client.post(
        f"/api/v1/submissions/{submission_id}/peer-reviews",
        headers=auth(owner["access_token"]),
        json={
            "rubric_scores": {
                "content": 4.5,
                "clarity": 4.5,
                "grammar": 4.5,
                "vocabulary": 4.5,
            },
            "feedback": "Clear idea and good supporting detail with a useful example.",
        },
    )
    assert review.status_code == 201, review.text
    assert review.json()["score"] == 9.0

    reviews = client.get(
        f"/api/v1/submissions/{submission_id}/peer-reviews",
        headers=auth(member["access_token"]),
    )
    assert reviews.status_code == 200, reviews.text
    assert reviews.json()[0]["reviewer_name"] == "Group Owner"

    leaderboard = client.get(
        "/api/v1/leaderboards?level=B1",
        headers=auth(owner["access_token"]),
    )
    assert leaderboard.status_code == 200, leaderboard.text
    entries = {item["display_name"]: item for item in leaderboard.json()["items"]}
    assert entries["Group Member"]["submissions_count"] == 1
    assert entries["Group Owner"]["peer_reviews_count"] == 1


def test_global_leaderboard_excludes_legacy_teacher_classes(client, db_session):
    learner = register(client, "legacy-class-learner@example.com", "Legacy Class Learner")
    teacher = register(client, "legacy-class-teacher@example.com", "Legacy Class Teacher")
    legacy_class = Classroom(
        name="Legacy Teacher Class",
        description="Compatibility class",
        teacher_id=teacher["user"]["id"],
        invite_code="LEGACY01",
        is_study_group=False,
    )
    db_session.add(legacy_class)
    db_session.flush()
    legacy_assignment = Assignment(
        class_id=legacy_class.id,
        created_by_id=teacher["user"]["id"],
        title="Legacy task",
        skill="writing",
        content="Write a sentence.",
        estimated_minutes=5,
        due_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(legacy_assignment)
    db_session.flush()
    db_session.add(
        AssignmentSubmission(
            assignment_id=legacy_assignment.id,
            learner_id=learner["user"]["id"],
            input_text="A legacy submission.",
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/leaderboards",
        headers=auth(learner["access_token"]),
    )

    assert response.status_code == 200, response.text
    entry = next(item for item in response.json()["items"] if item["display_name"] == "Legacy Class Learner")
    assert entry["submissions_count"] == 0
