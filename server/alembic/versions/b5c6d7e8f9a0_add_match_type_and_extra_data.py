"""add match_type and extra_data to matched_commit_pairs; make commit ids nullable

Revision ID: b5c6d7e8f9a0
Revises: a3b4c5d6e7f8
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matched_commit_pairs', recreate='always') as batch_op:
        batch_op.alter_column('commit_a_id', existing_type=sa.Text(), nullable=True)
        batch_op.alter_column('commit_b_id', existing_type=sa.Text(), nullable=True)
        batch_op.alter_column('timestamp_a', existing_type=sa.Text(), nullable=True)
        batch_op.alter_column('timestamp_b', existing_type=sa.Text(), nullable=True)
        batch_op.alter_column('who_first', existing_type=sa.Text(), nullable=True)
        batch_op.add_column(sa.Column('match_type', sa.Text(), nullable=False, server_default='sequential'))
        batch_op.add_column(sa.Column('extra_data', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('matched_commit_pairs', recreate='always') as batch_op:
        batch_op.drop_column('extra_data')
        batch_op.drop_column('match_type')
        batch_op.alter_column('who_first', existing_type=sa.Text(), nullable=False)
        batch_op.alter_column('timestamp_b', existing_type=sa.Text(), nullable=False)
        batch_op.alter_column('timestamp_a', existing_type=sa.Text(), nullable=False)
        batch_op.alter_column('commit_b_id', existing_type=sa.Text(), nullable=False)
        batch_op.alter_column('commit_a_id', existing_type=sa.Text(), nullable=False)
