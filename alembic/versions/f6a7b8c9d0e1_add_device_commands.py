"""add_device_commands

Revision ID: f6a7b8c9d0e1
Revises: d4e5f6a7b8c9
Create Date: 2026-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_commands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "device_id",
            sa.Integer(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "command_type",
            sa.Enum(
                "CHECK_IN",
                "UPDATE_INVENTORY",
                "LOCK",
                "UNLOCK",
                "WIPE",
                "RESTART",
                "SHUTDOWN",
                "LOST_MODE",
                name="commandtype",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "SENT",
                "ACKNOWLEDGED",
                "IN_PROGRESS",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="commandstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("result_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rabbitmq_message_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_device_commands_device_id", "device_commands", ["device_id"])
    op.create_index("ix_device_commands_status", "device_commands", ["status"])
    op.create_index("ix_device_commands_command_type", "device_commands", ["command_type"])
    op.create_index("ix_device_commands_created_at", "device_commands", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_device_commands_created_at", table_name="device_commands")
    op.drop_index("ix_device_commands_command_type", table_name="device_commands")
    op.drop_index("ix_device_commands_status", table_name="device_commands")
    op.drop_index("ix_device_commands_device_id", table_name="device_commands")
    op.drop_table("device_commands")
    op.execute("DROP TYPE IF EXISTS commandstatus")
    op.execute("DROP TYPE IF EXISTS commandtype")
