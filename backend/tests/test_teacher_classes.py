from datetime import UTC, datetime, timedelta

from assignment_job_helpers import complete_assignment_submission
from fastapi.testclient import TestClient
from job_helpers import complete_legacy_learning_path
from sqlalchemy import func, select

from app.models import Analysis, Assignment, LearnerProfile, User, utc_now


def register(client: TestClient, email: str, display_name: str = "Class User") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "safe-password-123", "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def set_role(db_session, email: str, role: str) -> None:
    user = db_session.scalar(select(User).where(func.lower(User.email) == email.lower()))
    assert user is not None
    user.role = role
    db_session.commit()


def future_deadline(days: int = 2) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def create_class(client: TestClient, teacher: dict, name: str = "IELTS Foundation") -> dict:
    response = client.post(
        "/api/v1/classes",
        headers=auth_header(teacher["access_token"]),
        json={"name": name, "description": "A private teacher-led class"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_can_promote_and_filter_teacher_role(client, db_session):
    admin = register(client, "teacher-role-admin@example.com", "Role Admin")
    teacher = register(client, "teacher-role@example.com", "Role Teacher")
    set_role(db_session, "teacher-role-admin@example.com", "admin")
    headers = auth_header(admin["access_token"])

    submitted = client.post(
        "/api/v1/teacher-applications",
        headers=auth_header(teacher["access_token"]),
        json={
            "motivation": (
                "I have taught English for several years and want to support learners "
                "in a structured classroom."
            ),
            "organization": "Community English Center",
        },
    )
    promoted = client.patch(
        f"/api/v1/admin/teacher-applications/{submitted.json()['id']}",
        headers=headers,
        json={"status": "approved"},
    )
    listed = client.get("/api/v1/admin/users?role=teacher", headers=headers)
    assert submitted.status_code == 201, submitted.text
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "approved"
    assert listed.status_code == 200
    assert any(item["id"] == teacher["user"]["id"] for item in listed.json()["items"])

    owned_class = create_class(client, teacher, "Protected Teacher Class")
    demoted = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=headers,
        json={"role": "learner"},
    )
    assert owned_class["teacher_id"] == teacher["user"]["id"]
    assert demoted.status_code == 409

    teacher_placement = client.get(
        "/api/v1/placement-test/latest",
        headers=auth_header(teacher["access_token"]),
    )
    teacher_home = client.get(
        "/api/v1/home",
        headers=auth_header(teacher["access_token"]),
    )
    teacher_placement_submit = client.post(
        "/api/v1/placement-test/submit",
        headers=auth_header(teacher["access_token"]),
        json={"answers": {f"q{index}": "a" for index in range(1, 21)}},
    )
    admin_placement = client.post(
        "/api/v1/placement-test/submit",
        headers=headers,
        json={"answers": {f"q{index}": "a" for index in range(1, 21)}},
    )
    assert teacher_placement.status_code == 404
    assert teacher_home.status_code == 200
    assert teacher_placement_submit.status_code == 201
    assert admin_placement.status_code == 403

    deactivated = client.patch(
        f"/api/v1/admin/users/{teacher['user']['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 409


def test_class_join_is_idempotent_and_membership_is_private(client, db_session):
    owner = register(client, "class-owner@example.com", "Owner Teacher")
    other_teacher = register(client, "class-other-teacher@example.com", "Other Teacher")
    learner = register(client, "class-member@example.com", "Member Learner")
    stranger = register(client, "class-stranger@example.com", "Stranger Learner")
    set_role(db_session, "class-owner@example.com", "teacher")
    set_role(db_session, "class-other-teacher@example.com", "teacher")

    denied = client.post(
        "/api/v1/classes",
        headers=auth_header(learner["access_token"]),
        json={"name": "Learner-owned class"},
    )
    assert denied.status_code == 403

    classroom = create_class(client, owner)
    assert classroom["invite_code"]
    for _ in range(2):
        joined = client.post(
            "/api/v1/classes/join",
            headers=auth_header(learner["access_token"]),
            json={"invite_code": classroom["invite_code"].lower()},
        )
        assert joined.status_code == 200
        assert joined.json()["id"] == classroom["id"]
        assert joined.json()["invite_code"] is None
        assert joined.json()["member_count"] == 1

    learner_classes = client.get(
        "/api/v1/classes",
        headers=auth_header(learner["access_token"]),
    )
    assert any(item["id"] == classroom["id"] for item in learner_classes.json()["items"])
    hidden = client.get(
        f"/api/v1/classes/{classroom['id']}",
        headers=auth_header(stranger["access_token"]),
    )
    learner_members = client.get(
        f"/api/v1/classes/{classroom['id']}/members",
        headers=auth_header(learner["access_token"]),
    )
    other_teacher_members = client.get(
        f"/api/v1/classes/{classroom['id']}/members",
        headers=auth_header(other_teacher["access_token"]),
    )
    owner_members = client.get(
        f"/api/v1/classes/{classroom['id']}/members",
        headers=auth_header(owner["access_token"]),
    )
    assert hidden.status_code == 404
    assert learner_members.status_code == 403
    assert other_teacher_members.status_code == 403
    assert owner_members.status_code == 200
    assert owner_members.json()["total"] == 1
    assert owner_members.json()["items"][0]["learner_id"] == learner["user"]["id"]

    set_role(db_session, "class-owner@example.com", "learner")
    former_owner_members = client.get(
        f"/api/v1/classes/{classroom['id']}/members",
        headers=auth_header(owner["access_token"]),
    )
    former_owner_detail = client.get(
        f"/api/v1/classes/{classroom['id']}",
        headers=auth_header(owner["access_token"]),
    )
    assert former_owner_members.status_code == 403
    assert former_owner_detail.status_code == 404


def test_assignment_analysis_feedback_and_space_isolation(client, db_session):
    owner = register(client, "assignment-owner@example.com", "Assignment Teacher")
    other_teacher = register(client, "assignment-other-teacher@example.com", "Other Teacher")
    learner = register(client, "assignment-member@example.com", "Assignment Learner")
    outsider = register(client, "assignment-outsider@example.com", "Outside Learner")
    set_role(db_session, "assignment-owner@example.com", "teacher")
    set_role(db_session, "assignment-other-teacher@example.com", "teacher")
    classroom = create_class(client, owner, "Work English")
    joined = client.post(
        "/api/v1/classes/join",
        headers=auth_header(learner["access_token"]),
        json={"invite_code": classroom["invite_code"]},
    )
    assert joined.status_code == 200
    class_space_id = joined.json()["learning_space_id"]
    assert class_space_id

    learner_headers = auth_header(learner["access_token"])
    preferences = client.patch(
        "/api/v1/onboarding/preferences",
        headers=learner_headers,
        json={"goal": "work", "daily_minutes": 30},
    )
    assert preferences.status_code == 200
    profile = db_session.get(LearnerProfile, learner["user"]["id"])
    assert profile is not None
    profile.onboarding_completed_at = utc_now()
    db_session.commit()
    path = complete_legacy_learning_path(
        client,
        learner["access_token"],
        {"goal": "Improve English for work", "current_level": "B1", "minutes_per_day": 30},
    )

    invalid_skill = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(owner["access_token"]),
        json={
            "title": "Invalid assignment",
            "skill": "listening",
            "content": "Listen and answer",
            "estimated_minutes": 15,
            "due_at": future_deadline(),
        },
    )
    expired_at_creation = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(owner["access_token"]),
        json={
            "title": "Already expired",
            "skill": "writing",
            "content": "Write a short answer",
            "estimated_minutes": 15,
            "due_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
    )
    assert invalid_skill.status_code == 422
    assert expired_at_creation.status_code == 422

    created = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(owner["access_token"]),
        json={
            "title": "Write a work email",
            "skill": "writing",
            "content": "Write a polite follow-up email to a colleague.",
            "estimated_minutes": 15,
            "due_at": future_deadline(),
        },
    )
    assert created.status_code == 201, created.text
    assignment = created.json()
    assert assignment["due_at"].endswith(("Z", "+00:00"))

    home = client.get("/api/v1/home", headers=learner_headers)
    assert home.status_code == 200, home.text
    assert home.json()["space_kind"] == "self"
    assert home.json()["goal"] == "Improve English for work"
    assert home.json()["daily_minutes"] == 30
    assert home.json()["class_assignment_minutes"] == 0
    assert home.json()["remaining_personal_minutes"] == 30
    assert home.json()["total_planned_minutes"] == 30
    assert home.json()["personal_learning_path"]["id"] == path["id"]
    assert home.json()["next_personal_task"] is not None

    class_headers = {
        **learner_headers,
        "X-Learning-Space-ID": class_space_id,
    }
    class_home = client.get("/api/v1/home", headers=class_headers)
    assert class_home.status_code == 200, class_home.text
    assert class_home.json()["space_kind"] == "class"
    assert class_home.json()["goal"] is None
    assert class_home.json()["class_assignment_minutes"] == 15
    assert class_home.json()["remaining_personal_minutes"] == 15
    assert class_home.json()["personal_learning_path"] is None
    assert class_home.json()["class_assignments"][0]["assignment_id"] == assignment["id"]
    assert class_home.json()["next_personal_task"] is None

    outsider_submit = client.post(
        f"/api/v1/assignments/{assignment['id']}/submit",
        headers=auth_header(outsider["access_token"]),
        json={"input_text": "This learner is not a class member."},
    )
    assert outsider_submit.status_code == 404

    submitted = complete_assignment_submission(
        client,
        assignment["id"],
        learner["access_token"],
        "Dear colleague, I am following up about our project meeting.",
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["analysis"]["type"] == "writing"
    submission_id = submitted.json()["id"]
    analysis_id = submitted.json()["analysis"]["id"]

    resubmitted = complete_assignment_submission(
        client,
        assignment["id"],
        learner["access_token"],
        "Dear colleague, could you please confirm our project meeting time?",
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["id"] == submission_id
    assert resubmitted.json()["analysis"]["id"] == analysis_id
    assert resubmitted.json()["input_text"].endswith("meeting time?")
    analysis_count = db_session.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.id == analysis_id)
    )
    assert analysis_count == 1

    other_teacher_submissions = client.get(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(other_teacher["access_token"]),
    )
    learner_feedback = client.patch(
        f"/api/v1/submissions/{submission_id}/feedback",
        headers=learner_headers,
        json={"feedback": "I should not be allowed to review myself."},
    )
    assert other_teacher_submissions.status_code == 403
    assert learner_feedback.status_code == 403

    feedback = client.patch(
        f"/api/v1/submissions/{submission_id}/feedback",
        headers=auth_header(owner["access_token"]),
        json={"feedback": "Clear tone. Add a specific requested response date."},
    )
    listed = client.get(
        f"/api/v1/assignments/{assignment['id']}/submissions",
        headers=auth_header(owner["access_token"]),
    )
    assert feedback.status_code == 200
    assert feedback.json()["status"] == "reviewed"
    assert feedback.json()["teacher_feedback"].startswith("Clear tone")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["learner_name"] == "Assignment Learner"

    own_submission = client.get(
        f"/api/v1/assignments/{assignment['id']}/submission",
        headers=learner_headers,
    )
    learner_assignments = client.get(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=learner_headers,
    )
    assert own_submission.status_code == 200
    assert own_submission.json()["id"] == submission_id
    assert own_submission.json()["teacher_feedback"].startswith("Clear tone")
    own_assignment = next(
        item for item in learner_assignments.json()["items"] if item["id"] == assignment["id"]
    )
    assert own_assignment["teacher_feedback"].startswith("Clear tone")

    regenerated = complete_legacy_learning_path(
        client,
        learner["access_token"],
        {
            "goal": "Prepare for study abroad",
            "current_level": "B2",
            "minutes_per_day": 60,
        },
    )
    refreshed_home = client.get("/api/v1/home", headers=learner_headers)
    assert refreshed_home.json()["goal"] == "Prepare for study abroad"
    assert refreshed_home.json()["daily_minutes"] == 60
    assert refreshed_home.json()["personal_learning_path"]["id"] == regenerated["id"]

    late_assignment = client.post(
        f"/api/v1/classes/{classroom['id']}/assignments",
        headers=auth_header(owner["access_token"]),
        json={
            "title": "Deadline check",
            "skill": "reading",
            "content": "Read this short paragraph and summarize it.",
            "estimated_minutes": 70,
            "due_at": future_deadline(),
        },
    )
    assert late_assignment.status_code == 201
    over_budget_home = client.get("/api/v1/home", headers=learner_headers)
    assert over_budget_home.json()["class_assignment_minutes"] == 0
    assert over_budget_home.json()["remaining_personal_minutes"] == 60
    assert over_budget_home.json()["next_personal_task"] is not None
    assert (
        over_budget_home.json()["total_planned_minutes"]
        == over_budget_home.json()["next_personal_task"]["duration_minutes"]
    )
    over_budget_class_home = client.get("/api/v1/home", headers=class_headers)
    assert over_budget_class_home.json()["class_assignment_minutes"] == 70
    assert over_budget_class_home.json()["remaining_personal_minutes"] == 0
    assert over_budget_class_home.json()["next_personal_task"] is None
    assert over_budget_class_home.json()["total_planned_minutes"] == 70
    db_session.expire_all()
    persisted_assignment = db_session.get(Assignment, late_assignment.json()["id"])
    assert persisted_assignment is not None
    persisted_assignment.due_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()
    late_submit = client.post(
        f"/api/v1/assignments/{persisted_assignment.id}/submit",
        headers=learner_headers,
        json={"input_text": "This submission is after the deadline."},
    )
    assert late_submit.status_code == 409
