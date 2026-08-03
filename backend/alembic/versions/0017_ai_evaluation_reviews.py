"""Add human-reviewed AI evaluation records.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_evaluation_reviews",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("case_id", sa.String(length=128), nullable=True),
        sa.Column("correctness", sa.Integer(), nullable=False),
        sa.Column("usefulness", sa.Integer(), nullable=False),
        sa.Column("level_fit", sa.Integer(), nullable=False),
        sa.Column("grounding", sa.Integer(), nullable=False),
        sa.Column("hallucination", sa.Integer(), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("analysis_id", "reviewer_id", name="uq_ai_evaluation_review_reviewer"),
    )
    op.create_index("ix_ai_evaluation_reviews_analysis_id", "ai_evaluation_reviews", ["analysis_id"])
    op.create_index("ix_ai_evaluation_reviews_reviewer_id", "ai_evaluation_reviews", ["reviewer_id"])
    op.create_index("ix_ai_evaluation_reviews_case_id", "ai_evaluation_reviews", ["case_id"])
    op.create_index("ix_ai_evaluation_reviews_created_at", "ai_evaluation_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_evaluation_reviews_created_at", table_name="ai_evaluation_reviews")
    op.drop_index("ix_ai_evaluation_reviews_case_id", table_name="ai_evaluation_reviews")
    op.drop_index("ix_ai_evaluation_reviews_reviewer_id", table_name="ai_evaluation_reviews")
    op.drop_index("ix_ai_evaluation_reviews_analysis_id", table_name="ai_evaluation_reviews")
    op.drop_table("ai_evaluation_reviews")
