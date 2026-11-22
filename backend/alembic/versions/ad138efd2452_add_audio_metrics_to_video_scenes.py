"""add_audio_metrics_to_video_scenes

Revision ID: ad138efd2452
Revises: 2ea329a2460e
Create Date: 2026-11-22 16:11:35.015899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad138efd2452'
down_revision: Union[str, None] = '2ea329a2460e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c["name"] for c in insp.get_columns("video_scenes")]
    if "audio_metrics" not in columns:
        op.add_column("video_scenes", sa.Column("audio_metrics", sa.JSON(), nullable=True))


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c["name"] for c in insp.get_columns("video_scenes")]
    if "audio_metrics" in columns:
        op.drop_column("video_scenes", "audio_metrics")
