from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    admin_audit_logs: Mapped[list[AdminAuditLog]] = relationship(
        back_populates="admin_user",
        foreign_keys="AdminAuditLog.admin_user_id",
    )
    taught_classes: Mapped[list[Classroom]] = relationship(
        back_populates="teacher",
        foreign_keys="Classroom.teacher_id",
    )
    class_memberships: Mapped[list[ClassMembership]] = relationship(
        back_populates="learner",
        cascade="all, delete-orphan",
        foreign_keys="ClassMembership.learner_id",
    )
    created_assignments: Mapped[list[ClassAssignment]] = relationship(
        back_populates="creator",
        foreign_keys="ClassAssignment.created_by",
    )
    assignment_submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="learner",
        cascade="all, delete-orphan",
        foreign_keys="AssignmentSubmission.learner_id",
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="analyses")
    assignment_submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="analysis",
        foreign_keys="AssignmentSubmission.analysis_id",
    )


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal: Mapped[str] = mapped_column(String(240))
    current_level: Mapped[str] = mapped_column(String(8))
    minutes_per_day: Mapped[int]
    plan: Mapped[dict] = mapped_column(JSON)
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    user: Mapped[User] = relationship(back_populates="learning_paths")


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


class Classroom(Base):
    __tablename__ = "classes"
    __table_args__ = (
        CheckConstraint(
            "target_level IS NULL OR target_level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
            name="ck_classes_target_level",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    teacher_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    target_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    join_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    teacher: Mapped[User] = relationship(
        back_populates="taught_classes",
        foreign_keys=[teacher_id],
    )
    memberships: Mapped[list[ClassMembership]] = relationship(
        back_populates="classroom",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[ClassAssignment]] = relationship(
        back_populates="classroom",
        cascade="all, delete-orphan",
    )


class ClassMembership(Base):
    __tablename__ = "class_memberships"
    __table_args__ = (
        UniqueConstraint("class_id", "learner_id", name="uq_class_memberships_class_learner"),
        CheckConstraint(
            "status IN ('pending', 'active', 'removed')",
            name="ck_class_memberships_status",
        ),
        Index("ix_class_memberships_class_status", "class_id", "status"),
        Index("ix_class_memberships_learner_status", "learner_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"),
        index=True,
    )
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classroom: Mapped[Classroom] = relationship(back_populates="memberships")
    learner: Mapped[User] = relationship(
        back_populates="class_memberships",
        foreign_keys=[learner_id],
    )


class ClassAssignment(Base):
    __tablename__ = "class_assignments"
    __table_args__ = (
        CheckConstraint(
            "skill_type IN ('reading', 'writing', 'speaking')",
            name="ck_class_assignments_skill_type",
        ),
        CheckConstraint(
            "target_level IS NULL OR target_level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
            name="ck_class_assignments_target_level",
        ),
        CheckConstraint(
            "status IN ('published', 'closed')",
            name="ck_class_assignments_status",
        ),
        Index("ix_class_assignments_class_status", "class_id", "status"),
        Index("ix_class_assignments_class_created_at", "class_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    class_id: Mapped[str] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"),
        index=True,
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160))
    instructions: Mapped[str] = mapped_column(Text)
    skill_type: Mapped[str] = mapped_column(String(32), index=True)
    target_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="published", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classroom: Mapped[Classroom] = relationship(back_populates="assignments")
    creator: Mapped[User] = relationship(
        back_populates="created_assignments",
        foreign_keys=[created_by],
    )
    submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "learner_id",
            "attempt_number",
            name="uq_assignment_submissions_attempt",
        ),
        CheckConstraint("attempt_number >= 1", name="ck_assignment_submissions_attempt_number"),
        CheckConstraint("status IN ('submitted')", name="ck_assignment_submissions_status"),
        Index(
            "ix_assignment_submissions_assignment_learner",
            "assignment_id",
            "learner_id",
        ),
        Index(
            "ix_assignment_submissions_assignment_submitted_at",
            "assignment_id",
            "submitted_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("class_assignments.id", ondelete="CASCADE"),
        index=True,
    )
    learner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("analyses.id", ondelete="RESTRICT"),
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    assignment: Mapped[ClassAssignment] = relationship(back_populates="submissions")
    learner: Mapped[User] = relationship(
        back_populates="assignment_submissions",
        foreign_keys=[learner_id],
    )
    analysis: Mapped[Analysis] = relationship(
        back_populates="assignment_submissions",
        foreign_keys=[analysis_id],
    )
