from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Learner")
    role: Mapped[str] = mapped_column(String(32), default="learner")
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learning_paths: Mapped[list[LearningPath]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    placement_attempts: Mapped[list[PlacementAttempt]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    vocabulary_items: Mapped[list[VocabularyItem]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learner_profile: Mapped[LearnerProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    owned_classes: Mapped[list[Classroom]] = relationship(
        back_populates="teacher",
        cascade="all, delete-orphan",
        foreign_keys="Classroom.teacher_id",
    )
    class_memberships: Mapped[list[ClassMember]] = relationship(
        back_populates="learner",
        cascade="all, delete-orphan",
    )
    created_assignments: Mapped[list[Assignment]] = relationship(
        back_populates="creator",
        foreign_keys="Assignment.created_by_id",
    )
    assignment_submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="learner",
        cascade="all, delete-orphan",
    )
    admin_audit_logs: Mapped[list[AdminAuditLog]] = relationship(
        back_populates="admin_user",
        foreign_keys="AdminAuditLog.admin_user_id",
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    input_text: Mapped[str] = mapped_column(Text)
    result: Mapped[dict] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    learning_path_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_day: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="analyses")
    learning_path: Mapped[LearningPath | None] = relationship(back_populates="analyses")


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal: Mapped[str] = mapped_column(String(240))
    current_level: Mapped[str] = mapped_column(String(8))
    minutes_per_day: Mapped[int]
    plan: Mapped[dict] = mapped_column(JSON)
    daily_progress: Mapped[dict] = mapped_column(JSON, default=dict)
    level_source: Mapped[str] = mapped_column(String(32), default="self_reported")
    placement_attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("placement_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="learning_paths")
    analyses: Mapped[list[Analysis]] = relationship(back_populates="learning_path")


class PlacementAttempt(Base):
    __tablename__ = "placement_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int]
    total_questions: Mapped[int]
    level: Mapped[str] = mapped_column(String(8))
    answers: Mapped[dict] = mapped_column(JSON)
    skill_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    test_version: Mapped[str] = mapped_column(String(32), default="2026-07-v1")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="placement_attempts")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    goal: Mapped[str | None] = mapped_column(String(240), nullable=True)
    daily_minutes: Mapped[int | None] = mapped_column(nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="learner_profile")


class Classroom(Base):
    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    invite_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    teacher: Mapped[User] = relationship(
        back_populates="owned_classes",
        foreign_keys=[teacher_id],
    )
    members: Mapped[list[ClassMember]] = relationship(
        back_populates="classroom",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="classroom",
        cascade="all, delete-orphan",
    )


class ClassMember(Base):
    __tablename__ = "class_members"
    __table_args__ = (UniqueConstraint("class_id", "learner_id", name="uq_class_member"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    classroom: Mapped[Classroom] = relationship(back_populates="members")
    learner: Mapped[User] = relationship(back_populates="class_memberships")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    skill: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    estimated_minutes: Mapped[int]
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classroom: Mapped[Classroom] = relationship(back_populates="assignments")
    creator: Mapped[User] = relationship(
        back_populates="created_assignments",
        foreign_keys=[created_by_id],
    )
    submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "learner_id", name="uq_assignment_submission_learner"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        index=True,
    )
    learner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    input_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="submitted", index=True)
    teacher_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    learner: Mapped[User] = relationship(back_populates="assignment_submissions")
    analysis: Mapped[Analysis | None] = relationship()


class VocabularyItem(Base):
    __tablename__ = "vocabulary_items"
    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_vocabulary_user_word"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    word: Mapped[str] = mapped_column(String(120))
    meaning: Mapped[str] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    review_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="vocabulary_items")


class WordLookupCache(Base):
    """Shared cache for external dictionary lookups.

    Not linked to any user – stores only public word data from
    dictionaryapi.dev and api.datamuse.com.
    Cache TTL: dictionary 30 days, datamuse 7 days.
    """

    __tablename__ = "word_lookup_cache"

    word: Mapped[str] = mapped_column(String(120), primary_key=True)
    dictionary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    datamuse: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dict_cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    datamuse_cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    admin_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    admin_user: Mapped[User | None] = relationship(
        back_populates="admin_audit_logs",
        foreign_keys=[admin_user_id],
    )
