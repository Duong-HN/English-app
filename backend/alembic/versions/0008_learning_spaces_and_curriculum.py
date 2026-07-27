"""Add isolated learning spaces and the fixed curriculum catalog.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-27
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_spaces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="self"),
        sa.Column("class_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("goal", sa.String(length=240), nullable=True),
        sa.Column("daily_minutes", sa.Integer(), nullable=True),
        sa.Column("current_level", sa.String(length=8), nullable=True),
        sa.Column("course_code", sa.String(length=80), nullable=True),
        sa.Column("mode_selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "class_id", name="uq_learning_space_user_class"),
    )
    op.create_index(op.f("ix_learning_spaces_user_id"), "learning_spaces", ["user_id"], unique=False)
    op.create_index(op.f("ix_learning_spaces_kind"), "learning_spaces", ["kind"], unique=False)
    op.create_index(op.f("ix_learning_spaces_class_id"), "learning_spaces", ["class_id"], unique=False)

    for table_name in ("analyses", "learning_paths", "placement_attempts", "vocabulary_items"):
        op.add_column(
            table_name,
            sa.Column("space_id", sa.String(length=64), nullable=True),
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_foreign_key(
                f"fk_{table_name}_space_id",
                "learning_spaces",
                ["space_id"],
                ["id"],
                ondelete="CASCADE",
            )
        op.create_index(op.f(f"ix_{table_name}_space_id"), table_name, ["space_id"], unique=False)

    with op.batch_alter_table("vocabulary_items") as batch_op:
        batch_op.drop_constraint("uq_vocabulary_user_word", type_="unique")
        batch_op.create_unique_constraint(
            "uq_vocabulary_user_space_word",
            ["user_id", "space_id", "word"],
        )

    op.create_table(
        "courses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False, server_default="core"),
        sa.Column("level", sa.String(length=8), nullable=True),
        sa.Column("band_min", sa.Float(), nullable=True),
        sa.Column("band_max", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_courses_code"), "courses", ["code"], unique=True)
    op.create_index(op.f("ix_courses_kind"), "courses", ["kind"], unique=False)
    op.create_index(op.f("ix_courses_level"), "courses", ["level"], unique=False)

    op.create_table(
        "course_units",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("unit_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "unit_number", name="uq_course_unit_number"),
    )
    op.create_index(op.f("ix_course_units_course_id"), "course_units", ["course_id"], unique=False)

    op.create_table(
        "lessons",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("unit_id", sa.String(length=64), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("skill", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(length=2048), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.ForeignKeyConstraint(["unit_id"], ["course_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_id", "lesson_number", name="uq_lesson_number"),
    )
    op.create_index(op.f("ix_lessons_unit_id"), "lessons", ["unit_id"], unique=False)
    op.create_index(op.f("ix_lessons_skill"), "lessons", ["skill"], unique=False)
    op.create_index(op.f("ix_lessons_content_type"), "lessons", ["content_type"], unique=False)

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("space_id", sa.String(length=64), nullable=False),
        sa.Column("lesson_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="started"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["space_id"], ["learning_spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "lesson_id", name="uq_lesson_progress_space"),
    )
    op.create_index(op.f("ix_lesson_progress_space_id"), "lesson_progress", ["space_id"], unique=False)
    op.create_index(op.f("ix_lesson_progress_lesson_id"), "lesson_progress", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_lesson_progress_status"), "lesson_progress", ["status"], unique=False)

    bind = op.get_bind()
    now = datetime.now(UTC)
    user_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM users"))]
    for user_id in user_ids:
        space_id = str(uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO learning_spaces "
                "(id, user_id, kind, name, mode_selected_at, created_at) "
                "VALUES (:id, :user_id, 'self', 'Tự học', :now, :now)"
            ),
            {"id": space_id, "user_id": user_id, "now": now},
        )
        for table_name in ("analyses", "learning_paths", "placement_attempts", "vocabulary_items"):
            bind.execute(
                sa.text(
                    f"UPDATE {table_name} SET space_id = :space_id "
                    "WHERE user_id = :user_id AND space_id IS NULL"
                ),
                {"space_id": space_id, "user_id": user_id},
            )


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_progress_status"), table_name="lesson_progress")
    op.drop_index(op.f("ix_lesson_progress_lesson_id"), table_name="lesson_progress")
    op.drop_index(op.f("ix_lesson_progress_space_id"), table_name="lesson_progress")
    op.drop_table("lesson_progress")

    op.drop_index(op.f("ix_lessons_content_type"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_skill"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_unit_id"), table_name="lessons")
    op.drop_table("lessons")

    op.drop_index(op.f("ix_course_units_course_id"), table_name="course_units")
    op.drop_table("course_units")

    op.drop_index(op.f("ix_courses_level"), table_name="courses")
    op.drop_index(op.f("ix_courses_kind"), table_name="courses")
    op.drop_index(op.f("ix_courses_code"), table_name="courses")
    op.drop_table("courses")

    with op.batch_alter_table("vocabulary_items") as batch_op:
        batch_op.drop_constraint("uq_vocabulary_user_space_word", type_="unique")
        batch_op.create_unique_constraint("uq_vocabulary_user_word", ["user_id", "word"])

    for table_name in ("vocabulary_items", "placement_attempts", "learning_paths", "analyses"):
        op.drop_index(op.f(f"ix_{table_name}_space_id"), table_name=table_name)
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(f"fk_{table_name}_space_id", type_="foreignkey")
            batch_op.drop_column("space_id")

    op.drop_index(op.f("ix_learning_spaces_class_id"), table_name="learning_spaces")
    op.drop_index(op.f("ix_learning_spaces_kind"), table_name="learning_spaces")
    op.drop_index(op.f("ix_learning_spaces_user_id"), table_name="learning_spaces")
    op.drop_table("learning_spaces")
