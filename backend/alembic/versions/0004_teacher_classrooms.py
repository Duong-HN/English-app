"""Add teacher classrooms, assignments, memberships, and submissions.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("teacher_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_level", sa.String(length=8), nullable=True),
        sa.Column("join_code", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "target_level IS NULL OR target_level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
            name="ck_classes_target_level",
        ),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_classes_created_at"), "classes", ["created_at"], unique=False)
    op.create_index(op.f("ix_classes_is_active"), "classes", ["is_active"], unique=False)
    op.create_index(op.f("ix_classes_join_code"), "classes", ["join_code"], unique=True)
    op.create_index(op.f("ix_classes_teacher_id"), "classes", ["teacher_id"], unique=False)

    op.create_table(
        "class_memberships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("class_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'removed')",
            name="ck_class_memberships_status",
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "class_id",
            "learner_id",
            name="uq_class_memberships_class_learner",
        ),
    )
    op.create_index(
        "ix_class_memberships_class_status",
        "class_memberships",
        ["class_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_class_memberships_learner_status",
        "class_memberships",
        ["learner_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_memberships_class_id"),
        "class_memberships",
        ["class_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_memberships_joined_at"),
        "class_memberships",
        ["joined_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_memberships_learner_id"),
        "class_memberships",
        ["learner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_memberships_status"),
        "class_memberships",
        ["status"],
        unique=False,
    )

    op.create_table(
        "class_assignments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("class_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("skill_type", sa.String(length=32), nullable=False),
        sa.Column("target_level", sa.String(length=8), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "skill_type IN ('reading', 'writing', 'speaking')",
            name="ck_class_assignments_skill_type",
        ),
        sa.CheckConstraint(
            "target_level IS NULL OR target_level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
            name="ck_class_assignments_target_level",
        ),
        sa.CheckConstraint(
            "status IN ('published', 'closed')",
            name="ck_class_assignments_status",
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_class_assignments_class_created_at",
        "class_assignments",
        ["class_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_class_assignments_class_status",
        "class_assignments",
        ["class_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_class_id"),
        "class_assignments",
        ["class_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_created_at"),
        "class_assignments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_created_by"),
        "class_assignments",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_due_at"),
        "class_assignments",
        ["due_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_skill_type"),
        "class_assignments",
        ["skill_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_class_assignments_status"),
        "class_assignments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "attempt_number >= 1",
            name="ck_assignment_submissions_attempt_number",
        ),
        sa.CheckConstraint(
            "status IN ('submitted')",
            name="ck_assignment_submissions_status",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["class_assignments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "learner_id",
            "attempt_number",
            name="uq_assignment_submissions_attempt",
        ),
    )
    op.create_index(
        "ix_assignment_submissions_assignment_learner",
        "assignment_submissions",
        ["assignment_id", "learner_id"],
        unique=False,
    )
    op.create_index(
        "ix_assignment_submissions_assignment_submitted_at",
        "assignment_submissions",
        ["assignment_id", "submitted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_submissions_analysis_id"),
        "assignment_submissions",
        ["analysis_id"],
        unique=False,
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
        op.f("ix_assignment_submissions_learner_id"),
        table_name="assignment_submissions",
    )
    op.drop_index(
        op.f("ix_assignment_submissions_assignment_id"),
        table_name="assignment_submissions",
    )
    op.drop_index(
        op.f("ix_assignment_submissions_analysis_id"),
        table_name="assignment_submissions",
    )
    op.drop_index(
        "ix_assignment_submissions_assignment_submitted_at",
        table_name="assignment_submissions",
    )
    op.drop_index(
        "ix_assignment_submissions_assignment_learner",
        table_name="assignment_submissions",
    )
    op.drop_table("assignment_submissions")

    op.drop_index(op.f("ix_class_assignments_status"), table_name="class_assignments")
    op.drop_index(op.f("ix_class_assignments_skill_type"), table_name="class_assignments")
    op.drop_index(op.f("ix_class_assignments_due_at"), table_name="class_assignments")
    op.drop_index(op.f("ix_class_assignments_created_by"), table_name="class_assignments")
    op.drop_index(op.f("ix_class_assignments_created_at"), table_name="class_assignments")
    op.drop_index(op.f("ix_class_assignments_class_id"), table_name="class_assignments")
    op.drop_index("ix_class_assignments_class_status", table_name="class_assignments")
    op.drop_index("ix_class_assignments_class_created_at", table_name="class_assignments")
    op.drop_table("class_assignments")

    op.drop_index(op.f("ix_class_memberships_status"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_learner_id"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_joined_at"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_class_id"), table_name="class_memberships")
    op.drop_index("ix_class_memberships_learner_status", table_name="class_memberships")
    op.drop_index("ix_class_memberships_class_status", table_name="class_memberships")
    op.drop_table("class_memberships")

    op.drop_index(op.f("ix_classes_teacher_id"), table_name="classes")
    op.drop_index(op.f("ix_classes_join_code"), table_name="classes")
    op.drop_index(op.f("ix_classes_is_active"), table_name="classes")
    op.drop_index(op.f("ix_classes_created_at"), table_name="classes")
    op.drop_table("classes")
