from datetime import timedelta
from uuid import uuid4

import pytest

from app.mcp_server import (
    get_class_summary,
    get_learner_progress,
    get_learning_path,
    list_pending_submissions,
    mcp,
    search_classes,
    search_learners,
    system_health,
)
from app.models import (
    Analysis,
    Assignment,
    AssignmentSubmission,
    ClassMember,
    Classroom,
    LearnerProfile,
    LearningPath,
    PlacementAttempt,
    User,
    VocabularyItem,
    utc_now,
)


@pytest.fixture
def mcp_records(db_session):
    suffix = uuid4().hex
    now = utc_now()
    teacher = User(
        id=f"teacher-{suffix}",
        email=f"teacher-{suffix}@example.com",
        display_name=f"MCP Teacher {suffix[:6]}",
        role="teacher",
    )
    learner = User(
        id=f"learner-{suffix}",
        email=f"learner-{suffix}@example.com",
        display_name=f"MCP Learner {suffix[:6]}",
        role="learner",
        level="B1",
    )
    classroom = Classroom(
        id=f"class-{suffix}",
        teacher_id=teacher.id,
        name=f"MCP English {suffix[:6]}",
        description="A class used to verify read-only MCP reporting.",
        invite_code=f"MCP{suffix[:8]}".upper(),
    )
    membership = ClassMember(
        id=f"membership-{suffix}",
        class_id=classroom.id,
        learner_id=learner.id,
    )
    profile = LearnerProfile(
        user_id=learner.id,
        goal="Improve workplace English",
        daily_minutes=30,
        onboarding_completed_at=now,
    )
    placement = PlacementAttempt(
        id=f"placement-{suffix}",
        user_id=learner.id,
        score=16,
        total_questions=20,
        level="B1",
        answers={"q1": "a"},
        skill_scores={"reading": {"percentage": 80}},
    )
    learning_path = LearningPath(
        id=f"path-{suffix}",
        user_id=learner.id,
        goal="Improve workplace English",
        current_level="B1",
        minutes_per_day=30,
        plan={
            "daily_tasks": [
                {"day": 1, "title": "Email review"},
                {"day": 2, "title": "Meeting practice"},
            ]
        },
        daily_progress={"1": {"completed": True}},
        level_source="placement",
        placement_attempt_id=placement.id,
    )
    submitted_analysis = Analysis(
        id=f"analysis-submitted-{suffix}",
        user_id=learner.id,
        type="writing",
        input_text="Could you confirm the meeting time?",
        result={"feedback": "Clear and polite."},
        score=8.0,
        provider="mock",
    )
    reviewed_analysis = Analysis(
        id=f"analysis-reviewed-{suffix}",
        user_id=learner.id,
        type="speaking",
        input_text="A short presentation transcript.",
        result={"feedback": "Add more supporting detail."},
        score=6.0,
        provider="mock",
    )
    vocabulary = VocabularyItem(
        id=f"vocabulary-{suffix}",
        user_id=learner.id,
        word="agenda",
        meaning="A list of items to discuss.",
        status="new",
    )
    submitted_assignment = Assignment(
        id=f"assignment-submitted-{suffix}",
        class_id=classroom.id,
        created_by_id=teacher.id,
        title="Write a meeting confirmation",
        skill="writing",
        content="Write a concise confirmation email.",
        estimated_minutes=20,
        due_at=now + timedelta(days=1),
    )
    overdue_assignment = Assignment(
        id=f"assignment-overdue-{suffix}",
        class_id=classroom.id,
        created_by_id=teacher.id,
        title="Past listening task",
        skill="listening",
        content="Summarize the recording.",
        estimated_minutes=15,
        due_at=now - timedelta(days=1),
    )
    reviewed_assignment = Assignment(
        id=f"assignment-reviewed-{suffix}",
        class_id=classroom.id,
        created_by_id=teacher.id,
        title="Present a project update",
        skill="speaking",
        content="Give a two-minute update.",
        estimated_minutes=20,
        due_at=now + timedelta(days=2),
    )
    submitted = AssignmentSubmission(
        id=f"submission-pending-{suffix}",
        assignment_id=submitted_assignment.id,
        learner_id=learner.id,
        analysis_id=submitted_analysis.id,
        input_text="Could you confirm the meeting time?",
        status="submitted",
        submitted_at=now - timedelta(hours=2),
    )
    reviewed = AssignmentSubmission(
        id=f"submission-reviewed-{suffix}",
        assignment_id=reviewed_assignment.id,
        learner_id=learner.id,
        analysis_id=reviewed_analysis.id,
        input_text="A short presentation transcript.",
        status="reviewed",
        teacher_feedback="Good structure.",
        submitted_at=now - timedelta(hours=1),
        feedback_at=now,
    )
    db_session.add_all([teacher, learner])
    db_session.flush()
    db_session.add_all([classroom, profile, placement, submitted_analysis, reviewed_analysis, vocabulary])
    db_session.flush()
    db_session.add_all(
        [
            membership,
            learning_path,
            submitted_assignment,
            overdue_assignment,
            reviewed_assignment,
        ]
    )
    db_session.flush()
    db_session.add_all([submitted, reviewed])
    db_session.commit()
    return {
        "learner": learner,
        "teacher": teacher,
        "classroom": classroom,
        "learning_path": learning_path,
        "pending_submission": submitted,
    }


@pytest.mark.asyncio
async def test_mcp_registers_only_read_only_tools(client):
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert names == {
        "system_health",
        "search_learners",
        "search_classes",
        "get_learning_path",
        "get_learner_progress",
        "get_class_summary",
        "list_pending_submissions",
    }
    assert all(tool.annotations is not None for tool in tools)
    assert all(tool.annotations.readOnlyHint is True for tool in tools if tool.annotations is not None)
    assert all(tool.annotations.destructiveHint is False for tool in tools if tool.annotations is not None)


def test_system_health_uses_test_database(client):
    result = system_health()
    assert result == {
        "status": "ready",
        "service": "LearnMate AI API",
        "environment": "test",
        "version": "0.7.0",
        "database": "ready",
    }


def test_search_and_learner_progress_include_bounded_operational_data(mcp_records):
    learner = mcp_records["learner"]
    found = search_learners(learner.email.split("@")[0], limit=5)
    assert [item["id"] for item in found["items"]] == [learner.id]

    progress = get_learner_progress(learner.id)
    assert progress["learner"]["display_name"] == learner.display_name
    assert progress["latest_placement"]["level"] == "B1"
    assert progress["current_learning_path"]["completed_days"] == [1]
    assert progress["current_learning_path"]["completion_percent"] == 50.0
    assert progress["analyses"]["total"] == 2
    assert progress["analyses"]["by_skill"]["writing"]["average_score"] == 8.0
    assert progress["vocabulary"] == {"total": 1, "by_status": {"new": 1}}
    assert progress["assignments"] == {
        "class_count": 1,
        "total": 3,
        "upcoming_unsubmitted": 0,
        "overdue_unsubmitted": 1,
        "awaiting_feedback": 1,
        "reviewed": 1,
    }

    path = get_learning_path(learner.id)
    assert path["learning_path"]["id"] == mcp_records["learning_path"].id
    assert len(path["learning_path"]["plan"]["daily_tasks"]) == 2


def test_class_summary_and_pending_queue_do_not_expose_invite_code(mcp_records):
    classroom = mcp_records["classroom"]
    found = search_classes(classroom.name, limit=5)
    assert [item["id"] for item in found["items"]] == [classroom.id]

    summary = get_class_summary(classroom.id)
    assert summary["class"]["name"] == classroom.name
    assert "invite_code" not in summary["class"]
    assert summary["members"] == {"total": 1, "levels": {"B1": 1}}
    assert summary["assignments"] == {"total": 3, "upcoming": 2, "past_due": 1}
    assert summary["submissions"] == {
        "total": 2,
        "awaiting_review": 1,
        "reviewed": 1,
        "average_score": 7.0,
    }

    queue = list_pending_submissions(classroom.id, limit=5)
    assert queue["total"] == 1
    assert queue["items"][0]["id"] == mcp_records["pending_submission"].id
    assert queue["items"][0]["analysis"]["score"] == 8.0
    assert queue["items"][0]["input_text"] == "Could you confirm the meeting time?"


def test_mcp_tools_reject_unknown_ids_and_unbounded_pages(client):
    with pytest.raises(ValueError, match="Learner not found"):
        get_learner_progress("missing-learner")
    with pytest.raises(ValueError, match="Class not found"):
        get_class_summary("missing-class")
    with pytest.raises(ValueError, match="limit must be between"):
        list_pending_submissions("missing-class", limit=51)
    with pytest.raises(ValueError, match="offset must be"):
        list_pending_submissions("missing-class", offset=-1)
