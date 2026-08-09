"""add acknowledged_at and completed_at to assignment tables

Revision ID: f1a2b3c4d5e6
Revises: ef0123456789
Create Date: 2026-08-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "ef0123456789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profile_assignments", sa.Column("acknowledged_at", sa.DateTime(), nullable=True))
    op.add_column("profile_assignments", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.add_column("mobile_app_assignments", sa.Column("acknowledged_at", sa.DateTime(), nullable=True))
    op.add_column("mobile_app_assignments", sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("mobile_app_assignments", "completed_at")
    op.drop_column("mobile_app_assignments", "acknowledged_at")
    op.drop_column("profile_assignments", "completed_at")
    op.drop_column("profile_assignments", "acknowledged_at")
