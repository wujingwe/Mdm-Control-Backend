"""migrate profile_scope to JSON scope column

Revision ID: 2b3c4d5e6f7a
Revises: 1a89b3e052f5
Create Date: 2026-07-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, Sequence[str], None] = "1a89b3e052f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("scope", sa.JSON(), nullable=False, server_default="{}"))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM profiles")).fetchall()
    for (profile_id,) in rows:
        scope_rows = conn.execute(
            sa.text("SELECT target_type, target_id FROM profile_scope WHERE profile_id = :pid"),
            {"pid": profile_id},
        ).fetchall()
        targets = [{"scope_type": t, "target_id": tid if tid else None} for t, tid in scope_rows]
        import json

        conn.execute(
            sa.text("UPDATE profiles SET scope = :scope WHERE id = :id"),
            {"scope": json.dumps({"targets": targets, "exclusions": []}), "id": profile_id},
        )

    op.drop_table("profile_scope")


def downgrade() -> None:
    op.create_table(
        "profile_scope",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("profile_id", "target_type", "target_id"),
    )
    op.create_index("ix_profile_scope_profile_id", "profile_scope", ["profile_id"])

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, scope FROM profiles")).fetchall()
    import json

    for profile_id, scope_json in rows:
        if scope_json:
            data = json.loads(scope_json) if isinstance(scope_json, str) else scope_json
            for target in data.get("targets", []):
                conn.execute(
                    sa.text("INSERT INTO profile_scope (profile_id, target_type, target_id) VALUES (:pid, :tt, :tid)"),
                    {"pid": profile_id, "tt": target["scope_type"], "tid": target.get("target_id") or 0},
                )

    op.drop_column("profiles", "scope")
