"""initial postgres schema (supabase)

Revision ID: 20260328_01
Revises:
Create Date: 2026-03-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260328_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("sub", sa.String(length=512), nullable=False),
        sa.Column("email", sa.String(length=512), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("handle", sa.String(length=256), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("sub"),
    )
    op.create_index(
        "ix_users_handle_unique",
        "users",
        ["handle"],
        unique=True,
        postgresql_where=sa.text("handle IS NOT NULL"),
    )

    op.create_table(
        "friend_edges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("from_sub", sa.String(length=512), nullable=False),
        sa.Column("to_sub", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_friend_pending_direction",
        "friend_edges",
        ["from_sub", "to_sub"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_friend_edges_to_status", "friend_edges", ["to_sub", "status"])
    op.create_index("ix_friend_edges_from_status", "friend_edges", ["from_sub", "status"])

    op.create_table(
        "drops",
        sa.Column("drop_id", sa.String(length=64), nullable=False),
        sa.Column("gemini_value", sa.Float(), nullable=False),
        sa.Column("classification", sa.String(length=256), nullable=True),
        sa.Column("image_base64", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("drop_id"),
    )

    op.create_table(
        "point_ledger",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_sub", sa.String(length=512), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("drop_id", sa.String(length=64), nullable=False),
        sa.Column("week_id", sa.String(length=16), nullable=False),
        sa.Column("gemini_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "drop_id", name="uq_point_ledger_user_drop"),
    )
    op.create_index(
        "ix_point_ledger_user_week",
        "point_ledger",
        ["user_sub", "week_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_point_ledger_user_week", table_name="point_ledger")
    op.drop_table("point_ledger")
    op.drop_table("drops")
    op.drop_index("ix_friend_edges_from_status", table_name="friend_edges")
    op.drop_index("ix_friend_edges_to_status", table_name="friend_edges")
    op.drop_index("uq_friend_pending_direction", table_name="friend_edges")
    op.drop_table("friend_edges")
    op.drop_index("ix_users_handle_unique", table_name="users")
    op.drop_table("users")
