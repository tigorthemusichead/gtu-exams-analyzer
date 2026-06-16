"""add_matched_commit_pairs

Revision ID: a3b4c5d6e7f8
Revises: e01628c26337
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'e01628c26337'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'matched_commit_pairs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('pair_id', sa.Integer(), nullable=False),
        sa.Column('commit_a_id', sa.Text(), nullable=False),
        sa.Column('commit_b_id', sa.Text(), nullable=False),
        sa.Column('jaccard_score', sa.Float(), nullable=False),
        sa.Column('timestamp_a', sa.Text(), nullable=False),
        sa.Column('timestamp_b', sa.Text(), nullable=False),
        sa.Column('diff_a', sa.Text(), nullable=True),
        sa.Column('diff_b', sa.Text(), nullable=True),
        sa.Column('exercise_id', sa.Text(), nullable=False),
        sa.Column('file_name', sa.Text(), nullable=False),
        sa.Column('who_first', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['pair_id'], ['similarity_pairs.pair_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_matched_commit_pairs_pair_id', 'matched_commit_pairs', ['pair_id'])


def downgrade() -> None:
    op.drop_index('ix_matched_commit_pairs_pair_id', table_name='matched_commit_pairs')
    op.drop_table('matched_commit_pairs')
