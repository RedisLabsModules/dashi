"""empty message

Revision ID: baa9adcbd1d5
Revises: c66db7eebd3b
Create Date: 2022-10-12 18:30:46.278797

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'baa9adcbd1d5'
down_revision = 'c66db7eebd3b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('benchmark',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('commitId', sa.Integer(), nullable=True),
    sa.Column('branch', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['commitId'], ['commits.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_benchmark_branch'), 'benchmark', ['branch'], unique=False)
    op.create_index(op.f('ix_benchmark_status'), 'benchmark', ['status'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_benchmark_status'), table_name='benchmark')
    op.drop_index(op.f('ix_benchmark_branch'), table_name='benchmark')
    op.drop_table('benchmark')
    # ### end Alembic commands ###
