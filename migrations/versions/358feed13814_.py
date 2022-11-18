"""empty message

Revision ID: 358feed13814
Revises: 8f78844e6b8a
Create Date: 2022-11-18 14:38:46.669760

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '358feed13814'
down_revision = '8f78844e6b8a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('benchmark', sa.Column('commit', sa.String(), nullable=True))
    op.create_index(op.f('ix_benchmark_commit'), 'benchmark', ['commit'], unique=False)
    op.drop_constraint('benchmark_commitId_fkey', 'benchmark', type_='foreignkey')
    op.drop_column('benchmark', 'commitId')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('benchmark', sa.Column('commitId', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('benchmark_commitId_fkey', 'benchmark', 'commits', ['commitId'], ['id'])
    op.drop_index(op.f('ix_benchmark_commit'), table_name='benchmark')
    op.drop_column('benchmark', 'commit')
    # ### end Alembic commands ###