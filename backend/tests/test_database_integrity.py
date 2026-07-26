from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text

from app.models import (
    Analysis,
    Assignment,
    AssignmentSubmission,
    ClassMember,
    Classroom,
    LearnerProfile,
    User,
    VocabularyItem,
)


def test_sqlite_enforces_foreign_keys_and_reference_actions(db_session):
    assert db_session.scalar(text("PRAGMA foreign_keys")) == 1

    teacher = User(
        email="fk-teacher@example.com",
        display_name="FK Teacher",
        role="teacher",
    )
    learner = User(email="fk-learner@example.com", display_name="FK Learner")
    learner.learner_profile = LearnerProfile(goal="work", daily_minutes=30)
    db_session.add_all([teacher, learner])
    db_session.flush()

    classroom = Classroom(
        teacher_id=teacher.id,
        name="Foreign Key Class",
        invite_code="FKTEST01",
    )
    db_session.add(classroom)
    db_session.flush()
    membership = ClassMember(class_id=classroom.id, learner_id=learner.id)
    assignment = Assignment(
        class_id=classroom.id,
        created_by_id=teacher.id,
        title="Reference actions",
        skill="reading",
        content="Read and summarize this database integrity prompt.",
        estimated_minutes=10,
        due_at=datetime.now(UTC) + timedelta(days=1),
    )
    analysis = Analysis(
        user_id=learner.id,
        type="reading",
        input_text="A short learner response.",
        result={"summary": "Short", "translation": "Ngắn", "vocabulary": [], "questions": []},
        provider="mock",
    )
    db_session.add_all([membership, assignment, analysis])
    db_session.flush()
    vocabulary = VocabularyItem(
        user_id=learner.id,
        analysis_id=analysis.id,
        word="integrity",
        meaning="tính toàn vẹn",
    )
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        learner_id=learner.id,
        analysis_id=analysis.id,
        input_text=analysis.input_text,
    )
    db_session.add_all([vocabulary, submission])
    db_session.commit()
    classroom_id = classroom.id
    membership_id = membership.id
    assignment_id = assignment.id
    submission_id = submission.id
    vocabulary_id = vocabulary.id

    db_session.execute(delete(Analysis).where(Analysis.id == analysis.id))
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(AssignmentSubmission, submission_id).analysis_id is None
    assert db_session.get(VocabularyItem, vocabulary_id).analysis_id is None

    db_session.execute(delete(User).where(User.id == teacher.id))
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(Classroom).where(Classroom.id == classroom_id))
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(ClassMember).where(ClassMember.id == membership_id)
        )
        == 0
    )
    assert (
        db_session.scalar(select(func.count()).select_from(Assignment).where(Assignment.id == assignment_id))
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(AssignmentSubmission)
            .where(AssignmentSubmission.id == submission_id)
        )
        == 0
    )
