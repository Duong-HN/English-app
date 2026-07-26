"""Add onboarding profiles, placement metadata and teacher classes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "placement_attempts",
        sa.Column("skill_scores", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "placement_attempts",
        sa.Column("test_version", sa.String(length=32), nullable=False, server_default="legacy-10q"),
    )

    op.create_table(
        "learner_profiles",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("goal", sa.String(length=240), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), nullable=True),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("teacher_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("invite_code", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_classes_teacher_id"), "classes", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_classes_invite_code"), "classes", ["invite_code"], unique=True)
    op.create_index(op.f("ix_classes_created_at"), "classes", ["created_at"], unique=False)

    op.create_table(
        "class_members",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("class_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "learner_id", name="uq_class_member"),
    )
    op.create_index(op.f("ix_class_members_class_id"), "class_members", ["class_id"], unique=False)
    op.create_index(
        op.f("ix_class_members_learner_id"),
        "class_members",
        ["learner_id"],
        unique=False,
    )

    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("class_id", sa.String(length=64), nullable=False),
        sa.Column("created_by_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("skill", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assignments_class_id"), "assignments", ["class_id"], unique=False)
    op.create_index(
        op.f("ix_assignments_created_by_id"),
        "assignments",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(op.f("ix_assignments_skill"), "assignments", ["skill"], unique=False)
    op.create_index(op.f("ix_assignments_due_at"), "assignments", ["due_at"], unique=False)
    op.create_index(op.f("ix_assignments_created_at"), "assignments", ["created_at"], unique=False)

    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "learner_id",
            name="uq_assignment_submission_learner",
        ),
    )
    op.create_index(
        op.f("ix_assignment_submissions_assignment_id"),
        "assignment_submissions",
        ["assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_submissions_learner_id"),
        "assignment_submissions",
        ["learner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_submissions_analysis_id"),
        "assignment_submissions",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_submissions_status"),
        "assignment_submissions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_submissions_submitted_at"),
        "assignment_submissions",
        ["submitted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_assignment_submissions_submitted_at"),
        table_name="assignment_submissions",
    )
    op.drop_index(op.f("ix_assignment_submissions_status"), table_name="assignment_submissions")
    op.drop_index(
        op.f("ix_assignment_submissions_analysis_id"),
        table_name="assignment_submissions",
    )
    op.drop_index(
        op.f("ix_assignment_submissions_learner_id"),
        table_name="assignment_submissions",
    )
    op.drop_index(
        op.f("ix_assignment_submissions_assignment_id"),
        table_name="assignment_submissions",
    )
    op.drop_table("assignment_submissions")

    op.drop_index(op.f("ix_assignments_created_at"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_due_at"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_skill"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_created_by_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_class_id"), table_name="assignments")
    op.drop_table("assignments")

    op.drop_index(op.f("ix_class_members_learner_id"), table_name="class_members")
    op.drop_index(op.f("ix_class_members_class_id"), table_name="class_members")
    op.drop_table("class_members")

    op.drop_index(op.f("ix_classes_created_at"), table_name="classes")
    op.drop_index(op.f("ix_classes_invite_code"), table_name="classes")
    op.drop_index(op.f("ix_classes_teacher_id"), table_name="classes")
    op.drop_table("classes")
    op.drop_table("learner_profiles")

    op.drop_column("placement_attempts", "test_version")
    op.drop_column("placement_attempts", "skill_scores")
