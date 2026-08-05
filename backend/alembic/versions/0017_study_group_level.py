"""Store the optional level of a collaborative study group.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("classes", sa.Column("level", sa.String(length=8), nullable=True))
    op.create_index(op.f("ix_classes_level"), "classes", ["level"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_classes_level"), table_name="classes")
    op.drop_column("classes", "level")
