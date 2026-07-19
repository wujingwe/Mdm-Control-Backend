"""simplify profile_assignments: drop source/source_id, update unique constraint

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-07-19 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_profile_assignments_profile_id", "profile_assignments")
    op.drop_index("ix_profile_assignments_device_id", "profile_assignments")
    op.drop_constraint(
        "uq_profile_assignments_profile_id_device_id",
        "profile_assignments",
        type_="unique",
    )
    op.drop_column("profile_assignments", "source")
    op.drop_column("profile_assignments", "source_id")
    op.create_unique_constraint(
        "uq_profile_assignments_profile_version_device",
        "profile_assignments",
        ["profile_id", "profile_version", "device_id"],
    )
    op.create_index(
        "ix_profile_assignments_profile_id",
        "profile_assignments",
        ["profile_id"],
    )
    op.create_index(
        "ix_profile_assignments_device_id",
        "profile_assignments",
        ["device_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profile_assignments_device_id", "profile_assignments")
    op.drop_index("ix_profile_assignments_profile_id", "profile_assignments")
    op.drop_constraint(
        "uq_profile_assignments_profile_version_device",
        "profile_assignments",
        type_="unique",
    )
    op.add_column(
        "profile_assignments",
        sa.Column("source", sa.String(20), nullable=False, server_default="DEVICE"),
    )
    op.add_column(
        "profile_assignments",
        sa.Column("source_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_profile_assignments_profile_id_device_id",
        "profile_assignments",
        ["profile_id", "device_id"],
    )
    op.create_index(
        "ix_profile_assignments_profile_id",
        "profile_assignments",
        ["profile_id"],
    )
    op.create_index(
        "ix_profile_assignments_device_id",
        "profile_assignments",
        ["device_id"],
    )
