"""rename enrollment_status to status on devices

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-07-19 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, Sequence[str], None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_devices_enrollment_status", "devices")
    op.alter_column("devices", "enrollment_status", new_column_name="status")
    op.create_index("ix_devices_status", "devices", ["status"])


def downgrade() -> None:
    op.drop_index("ix_devices_status", "devices")
    op.alter_column("devices", "status", new_column_name="enrollment_status")
    op.create_index("ix_devices_enrollment_status", "devices", ["enrollment_status"])
