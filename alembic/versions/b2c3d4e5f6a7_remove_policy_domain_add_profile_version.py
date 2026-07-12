"""Remove Policy domain, add Profile version column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop policy junction tables first (FK dependencies)
    op.drop_table("device_policies")
    op.drop_table("smart_group_policies")
    op.drop_table("static_group_policies")
    # Drop the policies table
    op.drop_table("policies")
    # Add version column to profiles
    op.add_column("profiles", sa.Column("version", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    # Remove version column from profiles
    op.drop_column("profiles", "version")
    # Recreate policies table
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("rollout_state", sa.String(length=20), nullable=False),
        sa.Column("target_devices", sa.Integer(), server_default="0", nullable=False),
        sa.Column("applied_devices", sa.Integer(), server_default="0", nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Recreate junction tables
    op.create_table(
        "device_policies",
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "smart_group_policies",
        sa.Column("smart_group_id", sa.Integer(), sa.ForeignKey("smart_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "static_group_policies",
        sa.Column("static_group_id", sa.Integer(), sa.ForeignKey("static_groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("policy_id", sa.Integer(), sa.ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True),
    )
