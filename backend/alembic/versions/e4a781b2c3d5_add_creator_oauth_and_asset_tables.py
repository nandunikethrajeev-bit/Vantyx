"""add_creator_oauth_and_asset_tables

Revision ID: e4a781b2c3d5
Revises: 1b1914c90953
Create Date: 2026-11-24 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a781b2c3d5'
down_revision: Union[str, None] = '1b1914c90953'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    # 1. Add OAuth & verification columns to creators table if not present
    existing_creator_cols = [c["name"] for c in insp.get_columns("creators")]
    creator_cols_to_add = [
        ("oauth_status", sa.String(32), "disconnected"),
        ("google_account_id", sa.String(128), None),
        ("google_account_email", sa.String(255), None),
        ("verified_channel_id", sa.String(128), None),
        ("verified_channel_title", sa.String(255), None),
        ("verified_at", sa.DateTime(timezone=True), None),
        ("access_token", sa.Text(), None),
        ("refresh_token", sa.Text(), None),
        ("token_expires_at", sa.DateTime(timezone=True), None),
        ("oauth_scopes", sa.String(512), None),
        ("is_revoked", sa.Boolean(), False),
        ("revoked_at", sa.DateTime(timezone=True), None),
        ("revocation_reason", sa.String(512), None),
    ]
    for col_name, col_type, default_val in creator_cols_to_add:
        if col_name not in existing_creator_cols:
            if default_val is not None:
                op.add_column("creators", sa.Column(col_name, col_type, server_default=sa.text(f"'{default_val}'" if isinstance(default_val, str) else str(default_val)), nullable=False if default_val is not None else True))
            else:
                op.add_column("creators", sa.Column(col_name, col_type, nullable=True))

    existing_indexes = [ix["name"] for ix in insp.get_indexes("creators")]
    if "ix_creators_oauth_status" not in existing_indexes:
        op.create_index("ix_creators_oauth_status", "creators", ["oauth_status"])
    if "ix_creators_verified_channel_id" not in existing_indexes:
        op.create_index("ix_creators_verified_channel_id", "creators", ["verified_channel_id"])

    # 2. Create creator_oauth_states table
    if "creator_oauth_states" not in tables:
        op.create_table(
            "creator_oauth_states",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("state", sa.String(128), unique=True, index=True, nullable=False),
            sa.Column("creator_id", sa.Integer(), sa.ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("redirect_uri", sa.String(512), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_used", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    # 3. Create creator_audit_logs table
    if "creator_audit_logs" not in tables:
        op.create_table(
            "creator_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("creator_id", sa.Integer(), sa.ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("event_type", sa.String(64), index=True, nullable=False),
            sa.Column("channel_id", sa.String(128), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    # 4. Create creator_asset_associations table
    if "creator_asset_associations" not in tables:
        op.create_table(
            "creator_asset_associations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("creator_id", sa.Integer(), sa.ForeignKey("creators.id", ondelete="CASCADE"), index=True, nullable=False),
            sa.Column("video_id", sa.String(128), index=True, nullable=False),
            sa.Column("asset_filename", sa.String(255), nullable=False),
            sa.Column("asset_path", sa.String(1024), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("duration_seconds", sa.Float(), server_default=sa.text("0.0"), nullable=False),
            sa.Column("is_verified", sa.Boolean(), server_default=sa.text("0"), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "creator_asset_associations" in tables:
        op.drop_table("creator_asset_associations")
    if "creator_audit_logs" in tables:
        op.drop_table("creator_audit_logs")
    if "creator_oauth_states" in tables:
        op.drop_table("creator_oauth_states")

    existing_indexes = [ix["name"] for ix in insp.get_indexes("creators")]
    if "ix_creators_verified_channel_id" in existing_indexes:
        op.drop_index("ix_creators_verified_channel_id", table_name="creators")
    if "ix_creators_oauth_status" in existing_indexes:
        op.drop_index("ix_creators_oauth_status", table_name="creators")

    creator_cols = [c["name"] for c in insp.get_columns("creators")]
    cols_to_drop = [
        "oauth_status", "google_account_id", "google_account_email",
        "verified_channel_id", "verified_channel_title", "verified_at",
        "access_token", "refresh_token", "token_expires_at", "oauth_scopes",
        "is_revoked", "revoked_at", "revocation_reason",
    ]
    for col_name in cols_to_drop:
        if col_name in creator_cols:
            op.drop_column("creators", col_name)
