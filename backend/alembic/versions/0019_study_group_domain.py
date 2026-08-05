"""Split study groups from legacy teacher classes.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "study_groups",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.String(length=8), nullable=True),
        sa.Column("invite_token", sa.String(length=64), nullable=False),
        sa.Column("member_limit", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_index(op.f("ix_study_groups_owner_id"), "study_groups", ["owner_id"], unique=False)
    op.create_index(op.f("ix_study_groups_level"), "study_groups", ["level"], unique=False)
    op.create_index(op.f("ix_study_groups_created_at"), "study_groups", ["created_at"], unique=False)

    op.create_table(
        "study_group_members",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["study_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_study_group_member"),
    )
    op.create_index(
        op.f("ix_study_group_members_group_id"), "study_group_members", ["group_id"], unique=False
    )
    op.create_index(op.f("ix_study_group_members_user_id"), "study_group_members", ["user_id"], unique=False)
    op.create_index(op.f("ix_study_group_members_status"), "study_group_members", ["status"], unique=False)

    op.create_table(
        "study_group_invitations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("inviter_id", sa.String(length=64), nullable=False),
        sa.Column("invitee_id", sa.String(length=64), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False, server_default="join_request"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["study_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invitee_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_study_group_invitations_group_id"), "study_group_invitations", ["group_id"], unique=False
    )
    op.create_index(
        op.f("ix_study_group_invitations_inviter_id"), "study_group_invitations", ["inviter_id"], unique=False
    )
    op.create_index(
        op.f("ix_study_group_invitations_invitee_id"), "study_group_invitations", ["invitee_id"], unique=False
    )
    op.create_index(
        op.f("ix_study_group_invitations_status"), "study_group_invitations", ["status"], unique=False
    )
    op.create_index(
        "ix_study_group_invitation_status",
        "study_group_invitations",
        ["group_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_study_group_invitations_expires_at"), "study_group_invitations", ["expires_at"], unique=False
    )
    op.create_index(
        op.f("ix_study_group_invitations_created_at"), "study_group_invitations", ["created_at"], unique=False
    )

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.alter_column("class_id", existing_type=sa.String(length=64), nullable=True)
        batch_op.add_column(sa.Column("study_group_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("review_deadline", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column("reviewers_per_submission", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("rubric", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_assignments_study_group_id",
            "study_groups",
            ["study_group_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_assignments_study_group_id", ["study_group_id"], unique=False)
        batch_op.create_index("ix_assignments_review_deadline", ["review_deadline"], unique=False)

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO study_groups
                (id, owner_id, name, description, level, invite_token, member_limit, created_at, updated_at)
            SELECT id, teacher_id, name, description, level, invite_code, 8, created_at, updated_at
            FROM classes
            WHERE is_study_group = :enabled
            """
        ),
        {"enabled": True},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO study_group_members
                (id, group_id, user_id, role, status, joined_at, left_at)
            SELECT id, class_id, learner_id, 'member', 'active', joined_at, NULL
            FROM class_members
            WHERE class_id IN (SELECT id FROM study_groups)
            """
        )
    )
    group_rows = bind.execute(sa.text("SELECT id, owner_id, created_at FROM study_groups")).mappings().all()
    for row in group_rows:
        has_owner = bind.execute(
            sa.text("SELECT 1 FROM study_group_members WHERE group_id = :group_id AND user_id = :user_id"),
            {"group_id": row["id"], "user_id": row["owner_id"]},
        ).first()
        if has_owner is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO study_group_members
                        (id, group_id, user_id, role, status, joined_at, left_at)
                    VALUES (:id, :group_id, :user_id, 'owner', 'active', :joined_at, NULL)
                    """
                ),
                {
                    "id": f"migrated-owner-{row['id']}",
                    "group_id": row["id"],
                    "user_id": row["owner_id"],
                    "joined_at": row["created_at"],
                },
            )
        else:
            bind.execute(
                sa.text(
                    "UPDATE study_group_members SET role = 'owner' "
                    "WHERE group_id = :group_id AND user_id = :user_id"
                ),
                {"group_id": row["id"], "user_id": row["owner_id"]},
            )
    bind.execute(
        sa.text(
            """
            UPDATE assignments
            SET study_group_id = class_id, class_id = NULL,
                rubric = NULL,
                review_deadline = due_at
            WHERE class_id IN (SELECT id FROM study_groups)
            """
        ),
    )

    op.create_table(
        "peer_review_allocations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["submission_id"], ["assignment_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "reviewer_id", name="uq_review_allocation_target"),
    )
    op.create_index(
        op.f("ix_peer_review_allocations_submission_id"),
        "peer_review_allocations",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_review_allocations_reviewer_id"),
        "peer_review_allocations",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peer_review_allocations_status"), "peer_review_allocations", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_peer_review_allocations_due_at"), "peer_review_allocations", ["due_at"], unique=False
    )
    op.create_index(
        op.f("ix_peer_review_allocations_created_at"), "peer_review_allocations", ["created_at"], unique=False
    )

    with op.batch_alter_table("peer_reviews") as batch_op:
        batch_op.add_column(sa.Column("allocation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("rubric_scores", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("quality_status", sa.String(length=24), nullable=False, server_default="accepted")
        )
        batch_op.add_column(sa.Column("flagged_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_peer_reviews_allocation_id",
            "peer_review_allocations",
            ["allocation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint("uq_peer_review_allocation", ["allocation_id"])
        batch_op.create_index("ix_peer_reviews_quality_status", ["quality_status"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_kind"), "notifications", ["kind"], unique=False)
    op.create_index(op.f("ix_notifications_read_at"), "notifications", ["read_at"], unique=False)
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False)

    op.create_table(
        "leaderboard_seasons",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("season_key", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_key"),
    )
    op.create_index(
        op.f("ix_leaderboard_seasons_starts_at"), "leaderboard_seasons", ["starts_at"], unique=False
    )
    op.create_index(op.f("ix_leaderboard_seasons_ends_at"), "leaderboard_seasons", ["ends_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE assignments SET class_id = study_group_id "
            "WHERE class_id IS NULL AND study_group_id IS NOT NULL"
        )
    )
    op.drop_index(op.f("ix_leaderboard_seasons_ends_at"), table_name="leaderboard_seasons")
    op.drop_index(op.f("ix_leaderboard_seasons_starts_at"), table_name="leaderboard_seasons")
    op.drop_table("leaderboard_seasons")
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_read_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_kind"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    with op.batch_alter_table("peer_reviews") as batch_op:
        batch_op.drop_index("ix_peer_reviews_quality_status")
        batch_op.drop_constraint("uq_peer_review_allocation", type_="unique")
        batch_op.drop_constraint("fk_peer_reviews_allocation_id", type_="foreignkey")
        batch_op.drop_column("flagged_reason")
        batch_op.drop_column("quality_status")
        batch_op.drop_column("rubric_scores")
        batch_op.drop_column("allocation_id")
    op.drop_index(op.f("ix_peer_review_allocations_created_at"), table_name="peer_review_allocations")
    op.drop_index(op.f("ix_peer_review_allocations_due_at"), table_name="peer_review_allocations")
    op.drop_index(op.f("ix_peer_review_allocations_status"), table_name="peer_review_allocations")
    op.drop_index(op.f("ix_peer_review_allocations_reviewer_id"), table_name="peer_review_allocations")
    op.drop_index(op.f("ix_peer_review_allocations_submission_id"), table_name="peer_review_allocations")
    op.drop_table("peer_review_allocations")
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_index("ix_assignments_review_deadline")
        batch_op.drop_index("ix_assignments_study_group_id")
        batch_op.drop_constraint("fk_assignments_study_group_id", type_="foreignkey")
        batch_op.drop_column("rubric")
        batch_op.drop_column("reviewers_per_submission")
        batch_op.drop_column("review_deadline")
        batch_op.drop_column("study_group_id")
        batch_op.alter_column("class_id", existing_type=sa.String(length=64), nullable=False)
    op.drop_index(op.f("ix_study_group_invitations_created_at"), table_name="study_group_invitations")
    op.drop_index(op.f("ix_study_group_invitations_expires_at"), table_name="study_group_invitations")
    op.drop_index(op.f("ix_study_group_invitations_status"), table_name="study_group_invitations")
    op.drop_index("ix_study_group_invitation_status", table_name="study_group_invitations")
    op.drop_index(op.f("ix_study_group_invitations_invitee_id"), table_name="study_group_invitations")
    op.drop_index(op.f("ix_study_group_invitations_inviter_id"), table_name="study_group_invitations")
    op.drop_index(op.f("ix_study_group_invitations_group_id"), table_name="study_group_invitations")
    op.drop_table("study_group_invitations")
    op.drop_index(op.f("ix_study_group_members_status"), table_name="study_group_members")
    op.drop_index(op.f("ix_study_group_members_user_id"), table_name="study_group_members")
    op.drop_index(op.f("ix_study_group_members_group_id"), table_name="study_group_members")
    op.drop_table("study_group_members")
    op.drop_index(op.f("ix_study_groups_created_at"), table_name="study_groups")
    op.drop_index(op.f("ix_study_groups_level"), table_name="study_groups")
    op.drop_index(op.f("ix_study_groups_owner_id"), table_name="study_groups")
    op.drop_table("study_groups")
