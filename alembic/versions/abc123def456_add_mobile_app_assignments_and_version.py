"""Add MobileAppAssignment table and rename mobile_apps.version → package_version

Revision ID: abc123def456
Revises: e8f9a0b1c2d3
Create Date: 2026-07-29 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "abc123def456"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("mobile_apps", "version", new_column_name="package_version", existing_type=sa.String(32))
    op.add_column("mobile_apps", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_table(
        "mobile_app_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mobile_app_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("desired_state", sa.String(length=10), nullable=False, server_default="PRESENT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mobile_app_id"], ["mobile_apps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mobile_app_id", "version", "device_id"),
    )
    op.create_index("ix_mobile_app_assignments_mobile_app_id", "mobile_app_assignments", ["mobile_app_id"])
    op.create_index("ix_mobile_app_assignments_device_id", "mobile_app_assignments", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_mobile_app_assignments_device_id", table_name="mobile_app_assignments")
    op.drop_index("ix_mobile_app_assignments_mobile_app_id", table_name="mobile_app_assignments")
    op.drop_table("mobile_app_assignments")
    op.drop_column("mobile_apps", "version")
    op.alter_column("mobile_apps", "package_version", new_column_name="version", existing_type=sa.String(32))
