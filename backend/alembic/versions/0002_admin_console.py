"""Add administrator activity and user-login metadata.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("admin_user_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_logs_admin_user_id"),
        "admin_audit_logs",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_action"),
        "admin_audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_target_type"),
        "admin_audit_logs",
        ["target_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_target_id"),
        "admin_audit_logs",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_created_at"),
        "admin_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_logs_created_at"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_target_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_target_type"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_admin_user_id"), table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "updated_at")
