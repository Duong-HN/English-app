"""Add persisted personalized learning paths.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("goal", sa.String(length=240), nullable=False),
        sa.Column("current_level", sa.String(length=8), nullable=False),
        sa.Column("minutes_per_day", sa.Integer(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_paths_user_id"), "learning_paths", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_learning_paths_created_at"),
        "learning_paths",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_learning_paths_created_at"), table_name="learning_paths")
    op.drop_index(op.f("ix_learning_paths_user_id"), table_name="learning_paths")
    op.drop_table("learning_paths")
