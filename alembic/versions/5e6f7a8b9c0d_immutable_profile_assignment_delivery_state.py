"""add immutable assignment delivery state

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-07-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5e6f7a8b9c0d"
down_revision: Union[str, Sequence[str], None] = "4d5e6f7a8b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profile_assignments",
        sa.Column("desired_state", sa.String(length=10), nullable=False, server_default="PRESENT"),
    )
    op.add_column(
        "profile_assignments",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "profile_assignments", sa.Column("last_attempt_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "profile_assignments", sa.Column("last_error", sa.Text(), nullable=True)
    )
    op.add_column(
        "profile_assignments", sa.Column("message_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "profile_assignments",
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE profile_assignments "
            "SET updated_at = assigned_at "
            "WHERE updated_at IS NULL"
        )
    )
    op.alter_column("profile_assignments", "desired_state", server_default=None)
    op.alter_column("profile_assignments", "attempt_count", server_default=None)


def downgrade() -> None:
    op.drop_column("profile_assignments", "updated_at")
    op.drop_column("profile_assignments", "message_id")
    op.drop_column("profile_assignments", "last_error")
    op.drop_column("profile_assignments", "last_attempt_at")
    op.drop_column("profile_assignments", "attempt_count")
    op.drop_column("profile_assignments", "desired_state")
