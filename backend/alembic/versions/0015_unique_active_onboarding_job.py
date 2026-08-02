"""Prevent duplicate active onboarding jobs per learning space.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_ONBOARDING_PREDICATE = "operation = 'onboarding' AND status IN ('queued', 'processing')"


def upgrade() -> None:
    op.create_index(
        "uq_learning_path_job_active_onboarding",
        "learning_path_jobs",
        ["user_id", "space_id"],
        unique=True,
        sqlite_where=sa.text(ACTIVE_ONBOARDING_PREDICATE),
        postgresql_where=sa.text(ACTIVE_ONBOARDING_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index("uq_learning_path_job_active_onboarding", table_name="learning_path_jobs")
