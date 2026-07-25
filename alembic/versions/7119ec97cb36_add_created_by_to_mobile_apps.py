"""add created_by to mobile_apps

Revision ID: 7119ec97cb36
Revises: b1a2c3d4e5f6
Create Date: 2026-07-26 10:02:14.419844

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7119ec97cb36"
down_revision: Union[str, Sequence[str], None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mobile_apps", sa.Column("created_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_mobile_apps_created_by", "mobile_apps", "users", ["created_by"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_mobile_apps_created_by", "mobile_apps", type_="foreignkey")
    op.drop_column("mobile_apps", "created_by")
