"""fix commands.created_by: backfill NULLs, enforce NOT NULL, fix FK

Revision ID: e8f9a0b1c2d3
Revises: 7119ec97cb36
Create Date: 2026-07-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "7119ec97cb36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULL created_by with admin user (id=1)
    op.execute("UPDATE commands SET created_by = 1 WHERE created_by IS NULL")

    # Drop ALL existing FK constraints on commands.created_by referencing users
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'commands' "
            "AND COLUMN_NAME = 'created_by' AND REFERENCED_TABLE_NAME = 'users'"
        )
    )
    for row in result:
        op.execute(f"ALTER TABLE commands DROP FOREIGN KEY `{row[0]}`")

    op.execute(
        "ALTER TABLE commands ADD CONSTRAINT fk_commands_created_by_users "
        "FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE"
    )

    # Enforce NOT NULL
    op.alter_column("commands", "created_by", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column("commands", "created_by", existing_type=sa.Integer(), nullable=True)
    op.execute("ALTER TABLE commands DROP FOREIGN KEY IF EXISTS fk_commands_created_by_users")
    op.execute(
        "ALTER TABLE commands ADD CONSTRAINT fk_commands_created_by_users "
        "FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL"
    )
