"""Add durable asynchronous learning-path jobs.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_path_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("space_id", sa.String(length=64), nullable=False),
        sa.Column("goal", sa.String(length=240), nullable=False),
        sa.Column("current_level", sa.String(length=8), nullable=False),
        sa.Column("minutes_per_day", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("learning_path_id", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["learning_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_learning_path_job_user_idempotency"),
    )
    op.create_index("ix_learning_path_jobs_user_id", "learning_path_jobs", ["user_id"])
    op.create_index("ix_learning_path_jobs_space_id", "learning_path_jobs", ["space_id"])
    op.create_index("ix_learning_path_jobs_idempotency_key", "learning_path_jobs", ["idempotency_key"])
    op.create_index("ix_learning_path_jobs_status", "learning_path_jobs", ["status"])
    op.create_index("ix_learning_path_jobs_available_at", "learning_path_jobs", ["available_at"])
    op.create_index("ix_learning_path_jobs_learning_path_id", "learning_path_jobs", ["learning_path_id"])
    op.create_index("ix_learning_path_jobs_created_at", "learning_path_jobs", ["created_at"])
    op.create_index(
        "ix_learning_path_jobs_status_available",
        "learning_path_jobs",
        ["status", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_learning_path_jobs_status_available", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_created_at", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_learning_path_id", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_available_at", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_status", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_idempotency_key", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_space_id", table_name="learning_path_jobs")
    op.drop_index("ix_learning_path_jobs_user_id", table_name="learning_path_jobs")
    op.drop_table("learning_path_jobs")
