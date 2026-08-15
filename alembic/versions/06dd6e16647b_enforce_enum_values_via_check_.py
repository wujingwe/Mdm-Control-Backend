"""enforce enum values via check constraints

Revision ID: 06dd6e16647b
Revises: e4a9cfcc56aa
Create Date: 2026-08-15 17:14:06.652473

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "06dd6e16647b"
down_revision: Union[str, Sequence[str], None] = "e4a9cfcc56aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_devices_connection_status",
        "devices",
        "connection_status IN ('CONNECTED', 'DISCONNECTED', 'UNKNOWN')",
    )
    op.create_check_constraint(
        "ck_devices_status",
        "devices",
        "status IN ('ENROLLED', 'UNENROLLED', 'PENDING', 'UNKNOWN')",
    )
    op.create_check_constraint(
        "ck_commands_command_type",
        "commands",
        "command_type IN ('CHECK_IN', 'LOCK', 'UNLOCK', 'WIPE', 'RESTART', 'SHUTDOWN')",
    )
    op.create_check_constraint(
        "ck_commands_status",
        "commands",
        "status IN ('PENDING', 'SENT', 'ACKNOWLEDGED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED')",
    )
    op.create_check_constraint(
        "ck_profile_assignments_status",
        "profile_assignments",
        "status IN ('PENDING', 'SENT', 'APPLIED', 'FAILED', 'REVOKE_PENDING', 'REVOKED')",
    )
    op.create_check_constraint(
        "ck_profile_assignments_desired_state",
        "profile_assignments",
        "desired_state IN ('PRESENT', 'ABSENT')",
    )
    op.create_check_constraint(
        "ck_mobile_app_assignments_status",
        "mobile_app_assignments",
        "status IN ('PENDING', 'SENT', 'APPLIED', 'FAILED', 'REVOKE_PENDING', 'REVOKED')",
    )
    op.create_check_constraint(
        "ck_mobile_app_assignments_desired_state",
        "mobile_app_assignments",
        "desired_state IN ('PRESENT', 'ABSENT')",
    )
    op.create_check_constraint(
        "ck_extension_attributes_data_type",
        "extension_attributes",
        "data_type IN ('STRING', 'INTEGER', 'DATE')",
    )
    op.create_check_constraint(
        "ck_extension_attributes_input_type",
        "extension_attributes",
        "input_type IN ('TEXT_FIELD', 'POPUP_MENU')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_extension_attributes_input_type", "extension_attributes", type_="check")
    op.drop_constraint("ck_extension_attributes_data_type", "extension_attributes", type_="check")
    op.drop_constraint("ck_mobile_app_assignments_desired_state", "mobile_app_assignments", type_="check")
    op.drop_constraint("ck_mobile_app_assignments_status", "mobile_app_assignments", type_="check")
    op.drop_constraint("ck_profile_assignments_desired_state", "profile_assignments", type_="check")
    op.drop_constraint("ck_profile_assignments_status", "profile_assignments", type_="check")
    op.drop_constraint("ck_commands_status", "commands", type_="check")
    op.drop_constraint("ck_commands_command_type", "commands", type_="check")
    op.drop_constraint("ck_devices_status", "devices", type_="check")
    op.drop_constraint("ck_devices_connection_status", "devices", type_="check")
