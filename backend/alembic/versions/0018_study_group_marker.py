"""Mark collaborative groups separately from legacy teacher classes.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "classes",
        sa.Column("is_study_group", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        op.f("ix_classes_is_study_group"),
        "classes",
        ["is_study_group"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_classes_is_study_group"), table_name="classes")
    op.drop_column("classes", "is_study_group")
