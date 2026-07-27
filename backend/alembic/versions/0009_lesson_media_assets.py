"""Add managed audio/video assets for curriculum lessons.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_media",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("lesson_id", sa.String(length=64), nullable=False),
        sa.Column("media_type", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("caption_url", sa.String(length=2048), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint(
            "lesson_id",
            "sort_order",
            "title",
            name="uq_lesson_media_position_title",
        ),
    )
    op.create_index(op.f("ix_lesson_media_lesson_id"), "lesson_media", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_lesson_media_media_type"), "lesson_media", ["media_type"], unique=False)
    op.create_index(op.f("ix_lesson_media_is_published"), "lesson_media", ["is_published"], unique=False)
    op.create_index(op.f("ix_lesson_media_created_by_id"), "lesson_media", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_lesson_media_created_at"), "lesson_media", ["created_at"], unique=False)

    op.add_column(
        "lesson_progress",
        sa.Column("media_progress", sa.JSON(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("lesson_id", sa.String(length=64), nullable=True),
    )
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.create_foreign_key(
            "fk_analyses_lesson_id",
            "lessons",
            ["lesson_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(op.f("ix_analyses_lesson_id"), "analyses", ["lesson_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_analyses_lesson_id"), table_name="analyses")
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("fk_analyses_lesson_id", type_="foreignkey")
        batch_op.drop_column("lesson_id")

    with op.batch_alter_table("lesson_progress") as batch_op:
        batch_op.drop_column("media_progress")

    op.drop_index(op.f("ix_lesson_media_created_at"), table_name="lesson_media")
    op.drop_index(op.f("ix_lesson_media_created_by_id"), table_name="lesson_media")
    op.drop_index(op.f("ix_lesson_media_is_published"), table_name="lesson_media")
    op.drop_index(op.f("ix_lesson_media_media_type"), table_name="lesson_media")
    op.drop_index(op.f("ix_lesson_media_lesson_id"), table_name="lesson_media")
    op.drop_table("lesson_media")
