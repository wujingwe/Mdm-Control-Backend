"""Add device_extension_attribute_values table and device relationships

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_extension_attribute_values",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extension_attribute_id", sa.Integer(), sa.ForeignKey("extension_attributes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("device_id", "extension_attribute_id"),
    )
    op.create_index("ix_device_ext_attr_device_id", "device_extension_attribute_values", ["device_id"])
    op.create_index("ix_device_ext_attr_attr_id", "device_extension_attribute_values", ["extension_attribute_id"])


def downgrade() -> None:
    op.drop_index("ix_device_ext_attr_attr_id", table_name="device_extension_attribute_values")
    op.drop_index("ix_device_ext_attr_device_id", table_name="device_extension_attribute_values")
    op.drop_table("device_extension_attribute_values")
