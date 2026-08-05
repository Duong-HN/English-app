"""Add device token registration and optional FCM delivery status.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(
            sa.Column("push_status", sa.String(length=16), nullable=False, server_default="skipped")
        )
        batch_op.add_column(sa.Column("push_error", sa.Text(), nullable=True))
        batch_op.create_index("ix_notifications_push_status", ["push_status"], unique=False)
        batch_op.alter_column("push_status", server_default=None)

    op.create_table(
        "push_devices",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_push_device_token"),
    )
    op.create_index(op.f("ix_push_devices_user_id"), "push_devices", ["user_id"], unique=False)
    op.create_index(op.f("ix_push_devices_platform"), "push_devices", ["platform"], unique=False)
    op.create_index(op.f("ix_push_devices_enabled"), "push_devices", ["enabled"], unique=False)
    op.create_index(op.f("ix_push_devices_last_seen_at"), "push_devices", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_push_devices_last_seen_at"), table_name="push_devices")
    op.drop_index(op.f("ix_push_devices_enabled"), table_name="push_devices")
    op.drop_index(op.f("ix_push_devices_platform"), table_name="push_devices")
    op.drop_index(op.f("ix_push_devices_user_id"), table_name="push_devices")
    op.drop_table("push_devices")

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_index("ix_notifications_push_status")
        batch_op.drop_column("push_error")
        batch_op.drop_column("push_status")
