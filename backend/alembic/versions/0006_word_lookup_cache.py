"""Add the shared external word lookup cache.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "word_lookup_cache",
        sa.Column("word", sa.String(length=120), nullable=False),
        sa.Column("dictionary", sa.JSON(), nullable=True),
        sa.Column("datamuse", sa.JSON(), nullable=True),
        sa.Column("dict_cached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("datamuse_cached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("word"),
    )


def downgrade() -> None:
    op.drop_table("word_lookup_cache")
