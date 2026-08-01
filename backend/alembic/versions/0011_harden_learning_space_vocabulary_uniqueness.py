"""Harden learning-space and vocabulary uniqueness invariants.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SELF_SPACE_PREDICATE = "kind = 'self' AND class_id IS NULL"


def upgrade() -> None:
    op.create_index(
        "uq_learning_space_user_self",
        "learning_spaces",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text(SELF_SPACE_PREDICATE),
        postgresql_where=sa.text(SELF_SPACE_PREDICATE),
    )

    op.add_column(
        "vocabulary_items",
        sa.Column("word_normalized", sa.String(length=120), nullable=True),
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE vocabulary_items SET word_normalized = lower(trim(word)) WHERE word_normalized IS NULL"
        )
    )
    duplicate = bind.execute(
        sa.text(
            "SELECT user_id, space_id, word_normalized, COUNT(*) AS total "
            "FROM vocabulary_items "
            "GROUP BY user_id, space_id, word_normalized "
            "HAVING COUNT(*) > 1 "
            "LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot apply vocabulary uniqueness migration: duplicate normalized words exist "
            f"for user_id={duplicate.user_id}, space_id={duplicate.space_id}, "
            f"word_normalized={duplicate.word_normalized}"
        )

    with op.batch_alter_table("vocabulary_items") as batch_op:
        batch_op.alter_column("word_normalized", existing_type=sa.String(length=120), nullable=False)
        batch_op.drop_constraint("uq_vocabulary_user_space_word", type_="unique")
        batch_op.create_unique_constraint(
            "uq_vocabulary_user_space_word",
            ["user_id", "space_id", "word_normalized"],
        )


def downgrade() -> None:
    with op.batch_alter_table("vocabulary_items") as batch_op:
        batch_op.drop_constraint("uq_vocabulary_user_space_word", type_="unique")
        batch_op.create_unique_constraint(
            "uq_vocabulary_user_space_word",
            ["user_id", "space_id", "word"],
        )
        batch_op.drop_column("word_normalized")
    op.drop_index("uq_learning_space_user_self", table_name="learning_spaces")
