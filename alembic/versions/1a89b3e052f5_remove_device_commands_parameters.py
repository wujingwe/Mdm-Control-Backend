"""remove device_commands.parameters

Revision ID: 1a89b3e052f5
Revises: f6a7b8c9d0e1
Create Date: 2026-07-18 13:51:55.754497

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1a89b3e052f5"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("device_commands", "parameters")


def downgrade() -> None:
    op.add_column("device_commands", sa.Column("parameters", sa.JSON(), nullable=True))
