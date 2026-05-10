"""fix check constraint on reports.score

Revision ID: 17d00414122b
Revises: df5a1987e179
Create Date: 2026-04-30 22:58:32.408279

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17d00414122b'
down_revision: Union[str, Sequence[str], None] = 'df5a1987e179'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_constraint('ck_reports_score_range', type_='check')

    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.create_check_constraint(
            constraint_name='ck_answers_score_range',
            condition='score >= 0.0 AND score <= 1.0'
        )


def downgrade():
    with op.batch_alter_table('answers', schema=None) as batch_op:
        batch_op.drop_constraint('ck_answers_score_range', type_='check')

    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.create_check_constraint(
            constraint_name='ck_reports_score_range',
            condition='score >= 0.0 AND score <= 1.0'
        )
