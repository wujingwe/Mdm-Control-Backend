"""improve schema integrity and add indexes

Revision ID: a1b2c3d4e5f6
Revises: 1e889c72d5ce
Create Date: 2026-07-12 15:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "1e889c72d5ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- devices: add onupdate trigger support (no DDL change, ORM-only) ---

    # --- users: add updated_at column ---
    op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("users", "updated_at", existing_type=sa.DateTime(), nullable=False)

    # --- created_by FK constraints ---
    op.create_foreign_key(
        "fk_smart_groups_created_by", "smart_groups", "users", ["created_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_static_groups_created_by", "static_groups", "users", ["created_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_profiles_created_by", "profiles", "users", ["created_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_extension_attributes_created_by",
        "extension_attributes",
        "users",
        ["created_by"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_inventory_searches_created_by",
        "inventory_searches",
        "users",
        ["created_by"],
        ["id"],
    )

    # --- junction table ON DELETE CASCADE ---
    op.drop_constraint("device_policies_ibfk_1", "device_policies", type_="foreignkey")
    op.drop_constraint("device_policies_ibfk_2", "device_policies", type_="foreignkey")
    op.create_foreign_key(
        "fk_device_policies_device_id",
        "device_policies",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_device_policies_policy_id",
        "device_policies",
        "policies",
        ["policy_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "smart_group_policies_ibfk_1", "smart_group_policies", type_="foreignkey"
    )
    op.drop_constraint(
        "smart_group_policies_ibfk_2", "smart_group_policies", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_smart_group_policies_group_id",
        "smart_group_policies",
        "smart_groups",
        ["smart_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_smart_group_policies_policy_id",
        "smart_group_policies",
        "policies",
        ["policy_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "static_group_policies_ibfk_1", "static_group_policies", type_="foreignkey"
    )
    op.drop_constraint(
        "static_group_policies_ibfk_2", "static_group_policies", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_static_group_policies_group_id",
        "static_group_policies",
        "static_groups",
        ["static_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_static_group_policies_policy_id",
        "static_group_policies",
        "policies",
        ["policy_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- static_group_devices: change FK from serial_number to device.id + CASCADE ---
    op.drop_constraint(
        "static_group_devices_ibfk_1", "static_group_devices", type_="foreignkey"
    )
    op.drop_constraint(
        "static_group_devices_ibfk_2", "static_group_devices", type_="foreignkey"
    )
    op.alter_column(
        "static_group_devices",
        "device_serial_number",
        new_column_name="device_id",
        existing_type=sa.String(30),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.execute(
        "UPDATE static_group_devices sgd "
        "INNER JOIN devices d ON d.serial_number = sgd.device_id "
        "SET sgd.device_id = d.id"
    )
    op.alter_column(
        "static_group_devices", "device_id", existing_type=sa.Integer(), nullable=False
    )
    op.create_foreign_key(
        "fk_static_group_devices_group_id",
        "static_group_devices",
        "static_groups",
        ["static_group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_static_group_devices_device_id",
        "static_group_devices",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- profile_scope: add unique constraint + index ---
    op.create_unique_constraint(
        "uq_profile_scope", "profile_scope", ["profile_id", "target_type", "target_id"]
    )
    op.create_index("ix_profile_scope_profile_id", "profile_scope", ["profile_id"])

    # --- profile_assignments: add CASCADE on device_id + indexes ---
    op.drop_constraint(
        "profile_assignments_ibfk_2", "profile_assignments", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_profile_assignments_device_id",
        "profile_assignments",
        "devices",
        ["device_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_profile_assignments_profile_id", "profile_assignments", ["profile_id"]
    )
    op.create_index(
        "ix_profile_assignments_device_id", "profile_assignments", ["device_id"]
    )

    # --- inventory_searches: add unique constraint on name ---
    op.create_unique_constraint(
        "uq_inventory_searches_name", "inventory_searches", ["name"]
    )

    # --- indexes on frequently queried columns ---
    op.create_index("ix_devices_connection_status", "devices", ["connection_status"])
    op.create_index("ix_devices_enrollment_status", "devices", ["enrollment_status"])
    op.create_index("ix_policies_rollout_state", "policies", ["rollout_state"])
    op.create_index("ix_smart_groups_created_by", "smart_groups", ["created_by"])
    op.create_index("ix_static_groups_created_by", "static_groups", ["created_by"])
    op.create_index("ix_profiles_created_by", "profiles", ["created_by"])
    op.create_index(
        "ix_extension_attributes_created_by", "extension_attributes", ["created_by"]
    )
    op.create_index(
        "ix_inventory_searches_created_by", "inventory_searches", ["created_by"]
    )


def downgrade() -> None:
    # --- drop indexes ---
    op.drop_index("ix_inventory_searches_created_by", "inventory_searches")
    op.drop_index("ix_extension_attributes_created_by", "extension_attributes")
    op.drop_index("ix_profiles_created_by", "profiles")
    op.drop_index("ix_static_groups_created_by", "static_groups")
    op.drop_index("ix_smart_groups_created_by", "smart_groups")
    op.drop_index("ix_policies_rollout_state", "policies")
    op.drop_index("ix_devices_enrollment_status", "devices")
    op.drop_index("ix_devices_connection_status", "devices")

    # --- remove inventory_searches unique constraint ---
    op.drop_constraint(
        "uq_inventory_searches_name", "inventory_searches", type_="unique"
    )

    # --- profile_assignments: revert CASCADE + indexes ---
    op.drop_index("ix_profile_assignments_device_id", "profile_assignments")
    op.drop_index("ix_profile_assignments_profile_id", "profile_assignments")
    op.drop_constraint(
        "fk_profile_assignments_device_id", "profile_assignments", type_="foreignkey"
    )
    op.create_foreign_key(
        "profile_assignments_ibfk_2",
        "profile_assignments",
        "devices",
        ["device_id"],
        ["id"],
    )

    # --- profile_scope: revert unique constraint + index ---
    op.drop_index("ix_profile_scope_profile_id", "profile_scope")
    op.drop_constraint("uq_profile_scope", "profile_scope", type_="unique")

    # --- static_group_devices: revert to serial_number FK ---
    op.drop_constraint(
        "fk_static_group_devices_device_id", "static_group_devices", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_static_group_devices_group_id", "static_group_devices", type_="foreignkey"
    )
    op.execute(
        "UPDATE static_group_devices sgd "
        "INNER JOIN devices d ON d.id = sgd.device_id "
        "SET sgd.device_id = d.serial_number"
    )
    op.alter_column(
        "static_group_devices",
        "device_id",
        new_column_name="device_serial_number",
        existing_type=sa.Integer(),
        type_=sa.String(30),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "static_group_devices_ibfk_2",
        "static_group_devices",
        "devices",
        ["device_serial_number"],
        ["serial_number"],
    )
    op.create_foreign_key(
        "static_group_devices_ibfk_1",
        "static_group_devices",
        "static_groups",
        ["static_group_id"],
        ["id"],
    )

    # --- junction tables: revert ON DELETE CASCADE ---
    op.drop_constraint(
        "fk_static_group_policies_policy_id",
        "static_group_policies",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_static_group_policies_group_id", "static_group_policies", type_="foreignkey"
    )
    op.create_foreign_key(
        "static_group_policies_ibfk_2",
        "static_group_policies",
        "policies",
        ["policy_id"],
        ["id"],
    )
    op.create_foreign_key(
        "static_group_policies_ibfk_1",
        "static_group_policies",
        "static_groups",
        ["static_group_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_smart_group_policies_policy_id", "smart_group_policies", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_smart_group_policies_group_id", "smart_group_policies", type_="foreignkey"
    )
    op.create_foreign_key(
        "smart_group_policies_ibfk_2",
        "smart_group_policies",
        "policies",
        ["policy_id"],
        ["id"],
    )
    op.create_foreign_key(
        "smart_group_policies_ibfk_1",
        "smart_group_policies",
        "smart_groups",
        ["smart_group_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_device_policies_policy_id", "device_policies", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_device_policies_device_id", "device_policies", type_="foreignkey"
    )
    op.create_foreign_key(
        "device_policies_ibfk_2", "device_policies", "policies", ["policy_id"], ["id"]
    )
    op.create_foreign_key(
        "device_policies_ibfk_1", "device_policies", "devices", ["device_id"], ["id"]
    )

    # --- created_by FK constraints ---
    op.drop_constraint(
        "fk_inventory_searches_created_by", "inventory_searches", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_extension_attributes_created_by", "extension_attributes", type_="foreignkey"
    )
    op.drop_constraint("fk_profiles_created_by", "profiles", type_="foreignkey")
    op.drop_constraint(
        "fk_static_groups_created_by", "static_groups", type_="foreignkey"
    )
    op.drop_constraint("fk_smart_groups_created_by", "smart_groups", type_="foreignkey")

    # --- users: drop updated_at ---
    op.drop_column("users", "updated_at")
