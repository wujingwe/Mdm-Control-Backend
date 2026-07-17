"""Comprehensive schema refactoring - enums, constraints, indexes, relationships

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- H4: Enum columns ---

    # Device connection_status: String -> Enum
    op.alter_column(
        "devices", "connection_status", type_=sa.String(20), existing_nullable=False
    )
    op.execute(
        "UPDATE devices SET connection_status = 'Online' WHERE connection_status NOT IN ('Online', 'Offline', 'Pending')"
    )
    # Device enrollment_status: String -> Enum
    op.alter_column(
        "devices", "enrollment_status", type_=sa.String(20), existing_nullable=False
    )
    op.execute(
        "UPDATE devices SET enrollment_status = 'Compliant' WHERE enrollment_status NOT IN ('Compliant', 'Non-compliant', 'Needs attention', 'Enrolled', 'Pending', 'Unknown')"
    )

    # ProfileScope target_type: String -> Enum
    op.execute(
        "UPDATE profile_scope SET target_id = 0 WHERE target_type = 'ALL_DEVICES' AND target_id IS NULL"
    )
    op.alter_column(
        "profile_scope", "target_type", type_=sa.String(20), existing_nullable=False
    )

    # H5: target_id NOT NULL
    op.alter_column(
        "profile_scope",
        "target_id",
        existing_type=sa.Integer,
        nullable=False,
        server_default="0",
    )

    # ProfileAssignment source: String -> Enum
    op.execute(
        "UPDATE profile_assignments SET source = 'ALL_DEVICES' WHERE source = 'SMART_GROUP' AND source_id IS NULL"
    )
    op.alter_column(
        "profile_assignments", "source", type_=sa.String(20), existing_nullable=False
    )

    # ProfileAssignment status: String -> Enum
    op.alter_column(
        "profile_assignments", "status", type_=sa.String(20), existing_nullable=False
    )

    # ExtensionAttribute data_type: String -> Enum
    op.execute(
        "UPDATE extension_attributes SET data_type = 'string' WHERE data_type = 'String'"
    )
    op.execute(
        "UPDATE extension_attributes SET data_type = 'integer' WHERE data_type = 'Integer'"
    )
    op.execute(
        "UPDATE extension_attributes SET data_type = 'date' WHERE data_type = 'Date'"
    )
    op.alter_column(
        "extension_attributes",
        "data_type",
        type_=sa.String(20),
        existing_nullable=False,
    )

    # ExtensionAttribute input_type: String -> Enum
    op.execute(
        "UPDATE extension_attributes SET input_type = 'Text field' WHERE input_type = 'Text'"
    )
    op.execute(
        "UPDATE extension_attributes SET input_type = 'Pop-up menu' WHERE input_type = 'Pop-up'"
    )
    op.alter_column(
        "extension_attributes",
        "input_type",
        type_=sa.String(20),
        existing_nullable=False,
    )

    # --- M1: SET NULL on created_by FKs ---
    op.alter_column(
        "smart_groups", "created_by", existing_type=sa.Integer, nullable=True
    )
    op.execute(
        "ALTER TABLE smart_groups DROP FOREIGN KEY IF EXISTS fk_smart_groups_created_by_users"
    )
    op.create_foreign_key(
        "fk_smart_groups_created_by_users",
        "smart_groups",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "static_groups", "created_by", existing_type=sa.Integer, nullable=True
    )
    op.execute(
        "ALTER TABLE static_groups DROP FOREIGN KEY IF EXISTS fk_static_groups_created_by_users"
    )
    op.create_foreign_key(
        "fk_static_groups_created_by_users",
        "static_groups",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("profiles", "created_by", existing_type=sa.Integer, nullable=True)
    op.execute(
        "ALTER TABLE profiles DROP FOREIGN KEY IF EXISTS fk_profiles_created_by_users"
    )
    op.create_foreign_key(
        "fk_profiles_created_by_users",
        "profiles",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "extension_attributes", "created_by", existing_type=sa.Integer, nullable=True
    )
    op.execute(
        "ALTER TABLE extension_attributes DROP FOREIGN KEY IF EXISTS fk_extension_attributes_created_by_users"
    )
    op.create_foreign_key(
        "fk_extension_attributes_created_by_users",
        "extension_attributes",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column(
        "inventory_searches", "created_by", existing_type=sa.Integer, nullable=True
    )
    op.execute(
        "ALTER TABLE inventory_searches DROP FOREIGN KEY IF EXISTS fk_inventory_searches_created_by_users"
    )
    op.create_foreign_key(
        "fk_inventory_searches_created_by_users",
        "inventory_searches",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- M4: Unique group names ---
    op.create_unique_constraint("uq_smart_groups_name", "smart_groups", ["name"])
    op.create_unique_constraint("uq_static_groups_name", "static_groups", ["name"])

    # --- L2: Timestamps on junction tables ---
    op.add_column(
        "static_group_devices", sa.Column("created_at", sa.DateTime(), nullable=True)
    )
    op.execute(
        "UPDATE static_group_devices SET created_at = NOW() WHERE created_at IS NULL"
    )
    op.alter_column("static_group_devices", "created_at", nullable=False)

    op.add_column(
        "profile_scope", sa.Column("created_at", sa.DateTime(), nullable=True)
    )
    op.execute("UPDATE profile_scope SET created_at = NOW() WHERE created_at IS NULL")
    op.alter_column("profile_scope", "created_at", nullable=False)

    op.add_column(
        "profile_assignments", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    # --- L4: Standardize description types ---
    op.alter_column(
        "smart_groups",
        "description",
        type_=sa.Text(),
        existing_type=sa.String(500),
        nullable=True,
    )
    op.alter_column(
        "static_groups",
        "description",
        type_=sa.Text(),
        existing_type=sa.String(500),
        nullable=True,
    )

    # --- L8: os_version index ---
    op.create_index("ix_devices_os_version", "devices", ["os_version"])


def downgrade() -> None:
    # Reverse all changes
    op.drop_index("ix_devices_os_version", table_name="devices")
    op.alter_column(
        "static_groups",
        "description",
        type_=sa.String(500),
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "smart_groups",
        "description",
        type_=sa.String(500),
        existing_type=sa.Text(),
        nullable=True,
    )

    op.drop_column("profile_assignments", "updated_at")
    op.drop_column("profile_scope", "created_at")
    op.drop_column("static_group_devices", "created_at")

    op.drop_constraint("uq_static_groups_name", "static_groups", type_="unique")
    op.drop_constraint("uq_smart_groups_name", "smart_groups", type_="unique")

    # Revert created_by to NOT NULL (would need data cleanup in production)
    op.execute(
        "ALTER TABLE inventory_searches DROP FOREIGN KEY fk_inventory_searches_created_by_users"
    )
    op.execute(
        "ALTER TABLE extension_attributes DROP FOREIGN KEY fk_extension_attributes_created_by_users"
    )
    op.execute("ALTER TABLE profiles DROP FOREIGN KEY fk_profiles_created_by_users")
    op.execute(
        "ALTER TABLE static_groups DROP FOREIGN KEY fk_static_groups_created_by_users"
    )
    op.execute(
        "ALTER TABLE smart_groups DROP FOREIGN KEY fk_smart_groups_created_by_users"
    )

    op.alter_column("inventory_searches", "created_by", nullable=False)
    op.alter_column("extension_attributes", "created_by", nullable=False)
    op.alter_column("profiles", "created_by", nullable=False)
    op.alter_column("static_groups", "created_by", nullable=False)
    op.alter_column("smart_groups", "created_by", nullable=False)

    # Revert enum columns back to String
    op.alter_column(
        "extension_attributes",
        "input_type",
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.alter_column(
        "extension_attributes",
        "data_type",
        type_=sa.String(20),
        existing_nullable=False,
    )
    op.alter_column(
        "profile_assignments", "status", type_=sa.String(20), existing_nullable=False
    )
    op.alter_column(
        "profile_assignments", "source", type_=sa.String(20), existing_nullable=False
    )
    op.alter_column("profile_scope", "target_id", type_=sa.Integer(), nullable=True)
    op.alter_column(
        "profile_scope", "target_type", type_=sa.String(20), existing_nullable=False
    )
    op.alter_column(
        "devices", "enrollment_status", type_=sa.String(20), existing_nullable=False
    )
    op.alter_column(
        "devices", "connection_status", type_=sa.String(20), existing_nullable=False
    )
