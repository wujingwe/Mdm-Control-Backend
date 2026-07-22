"""rename profile settings to policy

Revision ID: b1a2c3d4e5f6
Revises: 9003455e7d81
Create Date: 2026-07-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "5e6f7a8b9c0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename settings column to policy in profiles table."""
    op.alter_column("profiles", "settings", new_column_name="policy")


def downgrade() -> None:
    """Rename policy column back to settings in profiles table."""
    op.alter_column("profiles", "policy", new_column_name="settings")
