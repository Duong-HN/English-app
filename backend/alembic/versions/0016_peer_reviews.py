"""Add peer reviews for collaborative study groups.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-05
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
        "peer_reviews",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["assignment_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "submission_id",
            "reviewer_id",
            name="uq_peer_review_submission_reviewer",
        ),
    )
    op.create_index(
        op.f("ix_peer_reviews_submission_id"),
        "peer_reviews",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_reviews_reviewer_id"),
        "peer_reviews",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_reviews_created_at"),
        "peer_reviews",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_peer_reviews_created_at"), table_name="peer_reviews")
    op.drop_index(op.f("ix_peer_reviews_reviewer_id"), table_name="peer_reviews")
    op.drop_index(op.f("ix_peer_reviews_submission_id"), table_name="peer_reviews")
    op.drop_table("peer_reviews")
