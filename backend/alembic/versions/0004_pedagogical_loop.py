"""Add placement, progress, vocabulary and learning-context links.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "placement_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=8), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_placement_attempts_user_id"),
        "placement_attempts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_placement_attempts_completed_at"),
        "placement_attempts",
        ["completed_at"],
        unique=False,
    )

    op.add_column(
        "learning_paths",
        sa.Column("daily_progress", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "learning_paths",
        sa.Column("level_source", sa.String(length=32), nullable=False, server_default="self_reported"),
    )
    op.add_column(
        "learning_paths",
        sa.Column("placement_attempt_id", sa.String(length=64), nullable=True),
    )
    with op.batch_alter_table("learning_paths") as batch_op:
        batch_op.create_foreign_key(
            "fk_learning_paths_placement_attempt_id",
            "placement_attempts",
            ["placement_attempt_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        op.f("ix_learning_paths_placement_attempt_id"),
        "learning_paths",
        ["placement_attempt_id"],
        unique=False,
    )

    op.add_column("analyses", sa.Column("learning_path_id", sa.String(length=64), nullable=True))
    op.add_column("analyses", sa.Column("task_day", sa.Integer(), nullable=True))
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.create_foreign_key(
            "fk_analyses_learning_path_id",
            "learning_paths",
            ["learning_path_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(op.f("ix_analyses_learning_path_id"), "analyses", ["learning_path_id"], unique=False)

    op.create_table(
        "vocabulary_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=True),
        sa.Column("word", sa.String(length=120), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="new"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "word", name="uq_vocabulary_user_word"),
    )
    op.create_index(op.f("ix_vocabulary_items_user_id"), "vocabulary_items", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_vocabulary_items_analysis_id"),
        "vocabulary_items",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(op.f("ix_vocabulary_items_status"), "vocabulary_items", ["status"], unique=False)
    op.create_index(op.f("ix_vocabulary_items_created_at"), "vocabulary_items", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vocabulary_items_created_at"), table_name="vocabulary_items")
    op.drop_index(op.f("ix_vocabulary_items_status"), table_name="vocabulary_items")
    op.drop_index(op.f("ix_vocabulary_items_analysis_id"), table_name="vocabulary_items")
    op.drop_index(op.f("ix_vocabulary_items_user_id"), table_name="vocabulary_items")
    op.drop_table("vocabulary_items")

    op.drop_index(op.f("ix_analyses_learning_path_id"), table_name="analyses")
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("fk_analyses_learning_path_id", type_="foreignkey")
        batch_op.drop_column("task_day")
        batch_op.drop_column("learning_path_id")

    op.drop_index(op.f("ix_learning_paths_placement_attempt_id"), table_name="learning_paths")
    with op.batch_alter_table("learning_paths") as batch_op:
        batch_op.drop_constraint("fk_learning_paths_placement_attempt_id", type_="foreignkey")
        batch_op.drop_column("placement_attempt_id")
        batch_op.drop_column("level_source")
        batch_op.drop_column("daily_progress")

    op.drop_index(op.f("ix_placement_attempts_completed_at"), table_name="placement_attempts")
    op.drop_index(op.f("ix_placement_attempts_user_id"), table_name="placement_attempts")
    op.drop_table("placement_attempts")
