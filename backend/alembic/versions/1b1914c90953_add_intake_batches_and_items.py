"""add_intake_batches_and_items

Revision ID: 1b1914c90953
Revises: ad138efd2452
Create Date: 2026-11-22 18:11:45.551930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b1914c90953'
down_revision: Union[str, None] = 'ad138efd2452'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "intake_batches" not in tables:
        op.create_table(
            "intake_batches",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("batch_id", sa.String(length=64), nullable=False),
            sa.Column("creator_id", sa.Integer(), sa.ForeignKey("creators.id", ondelete="SET NULL"), nullable=True),
            sa.Column("total_submitted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_valid", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_duplicates", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_rejected", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_intake_batches_batch_id", "intake_batches", ["batch_id"], unique=True)
        op.create_index("ix_intake_batches_creator_id", "intake_batches", ["creator_id"])
        op.create_index("ix_intake_batches_status", "intake_batches", ["status"])

    if "intake_batch_items" not in tables:
        op.create_table(
            "intake_batch_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("batch_id", sa.Integer(), sa.ForeignKey("intake_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_id", sa.Integer(), sa.ForeignKey("video_sources.id", ondelete="SET NULL"), nullable=True),
            sa.Column("raw_url", sa.String(length=1024), nullable=False),
            sa.Column("canonical_url", sa.String(length=1024), nullable=True),
            sa.Column("video_id", sa.String(length=32), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_intake_batch_items_batch_id", "intake_batch_items", ["batch_id"])
        op.create_index("ix_intake_batch_items_source_id", "intake_batch_items", ["source_id"])
        op.create_index("ix_intake_batch_items_video_id", "intake_batch_items", ["video_id"])
        op.create_index("ix_intake_batch_items_status", "intake_batch_items", ["status"])


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "intake_batch_items" in tables:
        op.drop_table("intake_batch_items")
    if "intake_batches" in tables:
        op.drop_table("intake_batches")
