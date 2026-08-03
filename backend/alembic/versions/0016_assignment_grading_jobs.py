"""Add durable asynchronous assignment grading jobs.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assignment_grading_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), nullable=False),
        sa.Column("learner_id", sa.String(length=64), nullable=False),
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("skill", sa.String(length=32), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["assignment_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "learner_id",
            "idempotency_key",
            name="uq_assignment_grading_job_user_idempotency",
        ),
    )
    op.create_index("ix_assignment_grading_jobs_assignment_id", "assignment_grading_jobs", ["assignment_id"])
    op.create_index("ix_assignment_grading_jobs_learner_id", "assignment_grading_jobs", ["learner_id"])
    op.create_index("ix_assignment_grading_jobs_submission_id", "assignment_grading_jobs", ["submission_id"])
    op.create_index("ix_assignment_grading_jobs_skill", "assignment_grading_jobs", ["skill"])
    op.create_index(
        "ix_assignment_grading_jobs_idempotency_key",
        "assignment_grading_jobs",
        ["idempotency_key"],
    )
    op.create_index("ix_assignment_grading_jobs_status", "assignment_grading_jobs", ["status"])
    op.create_index("ix_assignment_grading_jobs_available_at", "assignment_grading_jobs", ["available_at"])
    op.create_index("ix_assignment_grading_jobs_analysis_id", "assignment_grading_jobs", ["analysis_id"])
    op.create_index("ix_assignment_grading_jobs_created_at", "assignment_grading_jobs", ["created_at"])
    op.create_index(
        "ix_assignment_grading_jobs_status_available",
        "assignment_grading_jobs",
        ["status", "available_at"],
    )
    op.create_index(
        "uq_assignment_grading_job_active_submission",
        "assignment_grading_jobs",
        ["assignment_id", "learner_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'processing')"),
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )


def downgrade() -> None:
    for name in (
        "uq_assignment_grading_job_active_submission",
        "ix_assignment_grading_jobs_status_available",
        "ix_assignment_grading_jobs_created_at",
        "ix_assignment_grading_jobs_analysis_id",
        "ix_assignment_grading_jobs_available_at",
        "ix_assignment_grading_jobs_status",
        "ix_assignment_grading_jobs_idempotency_key",
        "ix_assignment_grading_jobs_skill",
        "ix_assignment_grading_jobs_submission_id",
        "ix_assignment_grading_jobs_learner_id",
        "ix_assignment_grading_jobs_assignment_id",
    ):
        op.drop_index(name, table_name="assignment_grading_jobs")
    op.drop_table("assignment_grading_jobs")
