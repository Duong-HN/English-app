"""Add the learner-to-teacher application workflow.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teacher_applications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("motivation", sa.Text(), nullable=False),
        sa.Column("organization", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.String(length=64), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_teacher_application_user"),
    )
    op.create_index(
        op.f("ix_teacher_applications_user_id"),
        "teacher_applications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_teacher_applications_status"),
        "teacher_applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_teacher_applications_reviewed_by_id"),
        "teacher_applications",
        ["reviewed_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_teacher_applications_requested_at"),
        "teacher_applications",
        ["requested_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_teacher_applications_requested_at"), table_name="teacher_applications")
    op.drop_index(op.f("ix_teacher_applications_reviewed_by_id"), table_name="teacher_applications")
    op.drop_index(op.f("ix_teacher_applications_status"), table_name="teacher_applications")
    op.drop_index(op.f("ix_teacher_applications_user_id"), table_name="teacher_applications")
    op.drop_table("teacher_applications")
