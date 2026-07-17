"""add network and certificates to devices

Revision ID: 1367b77be087
Revises: 505f92c76c57
Create Date: 2026-06-20 21:09:08.028165

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "1367b77be087"
down_revision: Union[str, Sequence[str], None] = "505f92c76c57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # rename columns — preserves existing data
    op.alter_column(
        "devices",
        "serial",
        new_column_name="serial_number",
        existing_type=sa.String(30),
        existing_nullable=False,
    )
    op.alter_column(
        "devices",
        "battery_level",
        new_column_name="battery_status",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )

    # add new columns as nullable so existing rows are accepted
    op.add_column(
        "devices", sa.Column("connection_status", sa.String(20), nullable=True)
    )
    op.add_column(
        "devices", sa.Column("enrollment_status", sa.String(20), nullable=True)
    )
    op.add_column("devices", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("devices", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column(
        "devices", sa.Column("last_enrolled_at", sa.DateTime(), nullable=True)
    )
    op.add_column("devices", sa.Column("network", sa.JSON(), nullable=True))
    op.add_column("devices", sa.Column("certificates", sa.JSON(), nullable=True))

    # backfill from old columns
    op.execute(
        "UPDATE devices SET "
        "connection_status = status, "
        "enrollment_status = 'Enrolled', "
        "created_at = NOW(), "
        "updated_at = NOW(), "
        "last_enrolled_at = NOW()"
    )

    # drop removed columns
    op.drop_column("devices", "status")
    op.drop_column("devices", "cpu_usage")
    op.drop_column("devices", "last_boot")
    op.drop_column("devices", "compliance")
    op.drop_column("devices", "last_seen")
    op.drop_column("devices", "owner")
    op.drop_column("devices", "signal_strength")

    # make required columns non-nullable now that data exists
    op.alter_column(
        "devices",
        "connection_status",
        existing_type=sa.String(20),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "devices",
        "enrollment_status",
        existing_type=sa.String(20),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "devices",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "devices",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "devices",
        "last_enrolled_at",
        existing_type=sa.DateTime(),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    # make columns nullable so we can backfill old data
    op.alter_column(
        "devices",
        "connection_status",
        existing_type=sa.String(20),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "devices",
        "enrollment_status",
        existing_type=sa.String(20),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "devices",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "devices",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "devices",
        "last_enrolled_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        nullable=True,
    )

    # add back removed columns
    op.add_column("devices", sa.Column("status", sa.String(20), nullable=True))
    op.add_column("devices", sa.Column("cpu_usage", sa.Integer(), nullable=True))
    op.add_column("devices", sa.Column("last_boot", sa.String(30), nullable=True))
    op.add_column("devices", sa.Column("compliance", sa.String(50), nullable=True))
    op.add_column("devices", sa.Column("last_seen", sa.String(20), nullable=True))
    op.add_column("devices", sa.Column("owner", sa.String(50), nullable=True))
    op.add_column("devices", sa.Column("signal_strength", sa.String(10), nullable=True))

    # backfill status from connection_status
    op.execute("UPDATE devices SET status = connection_status")

    # drop new columns
    op.drop_column("devices", "certificates")
    op.drop_column("devices", "network")
    op.drop_column("devices", "last_enrolled_at")
    op.drop_column("devices", "updated_at")
    op.drop_column("devices", "created_at")
    op.drop_column("devices", "enrollment_status")
    op.drop_column("devices", "connection_status")

    # rename back
    op.alter_column(
        "devices",
        "battery_status",
        new_column_name="battery_level",
        existing_type=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "devices",
        "serial_number",
        new_column_name="serial",
        existing_type=sa.String(30),
        existing_nullable=False,
    )
