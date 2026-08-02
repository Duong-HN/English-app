"""Add operation type to learning-path jobs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "learning_path_jobs",
        sa.Column("operation", sa.String(length=16), nullable=False, server_default="generate"),
    )
    op.create_index("ix_learning_path_jobs_operation", "learning_path_jobs", ["operation"])


def downgrade() -> None:
    op.drop_index("ix_learning_path_jobs_operation", table_name="learning_path_jobs")
    op.drop_column("learning_path_jobs", "operation")
