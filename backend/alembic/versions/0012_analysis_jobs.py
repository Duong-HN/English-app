"""Add durable asynchronous AI analysis jobs.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("space_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("lesson_id", sa.String(length=64), nullable=True),
        sa.Column("learning_path_id", sa.String(length=64), nullable=True),
        sa.Column("task_day", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["learning_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_analysis_job_user_idempotency"),
    )
    op.create_index("ix_analysis_jobs_user_id", "analysis_jobs", ["user_id"])
    op.create_index("ix_analysis_jobs_space_id", "analysis_jobs", ["space_id"])
    op.create_index("ix_analysis_jobs_type", "analysis_jobs", ["type"])
    op.create_index("ix_analysis_jobs_lesson_id", "analysis_jobs", ["lesson_id"])
    op.create_index("ix_analysis_jobs_learning_path_id", "analysis_jobs", ["learning_path_id"])
    op.create_index("ix_analysis_jobs_idempotency_key", "analysis_jobs", ["idempotency_key"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_available_at", "analysis_jobs", ["available_at"])
    op.create_index(
        "ix_analysis_jobs_status_available",
        "analysis_jobs",
        ["status", "available_at"],
    )
    op.create_index("ix_analysis_jobs_analysis_id", "analysis_jobs", ["analysis_id"])
    op.create_index("ix_analysis_jobs_created_at", "analysis_jobs", ["created_at"])


def downgrade() -> None:
    for name in (
        "ix_analysis_jobs_created_at",
        "ix_analysis_jobs_analysis_id",
        "ix_analysis_jobs_status_available",
        "ix_analysis_jobs_available_at",
        "ix_analysis_jobs_status",
        "ix_analysis_jobs_idempotency_key",
        "ix_analysis_jobs_learning_path_id",
        "ix_analysis_jobs_lesson_id",
        "ix_analysis_jobs_type",
        "ix_analysis_jobs_space_id",
        "ix_analysis_jobs_user_id",
    ):
        op.drop_index(name, table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
