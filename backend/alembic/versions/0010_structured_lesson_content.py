"""Store structured lesson activities and content provenance.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("content_pack", sa.JSON(), nullable=True))
    op.add_column("lessons", sa.Column("source_attribution", sa.String(length=500), nullable=True))
    op.add_column("lessons", sa.Column("license_name", sa.String(length=160), nullable=True))


def downgrade() -> None:
    op.drop_column("lessons", "license_name")
    op.drop_column("lessons", "source_attribution")
    op.drop_column("lessons", "content_pack")
