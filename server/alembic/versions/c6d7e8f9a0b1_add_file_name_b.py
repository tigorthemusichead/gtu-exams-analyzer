"""add file_name_b to matched_commit_pairs for cross-file renamed matches

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, Sequence[str], None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matched_commit_pairs', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('file_name_b', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('matched_commit_pairs', recreate='always') as batch_op:
        batch_op.drop_column('file_name_b')
