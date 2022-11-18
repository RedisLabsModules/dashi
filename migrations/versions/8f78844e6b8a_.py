"""empty message

Revision ID: 8f78844e6b8a
Revises: 1eba2a35a275
Create Date: 2022-11-18 14:05:05.230452

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f78844e6b8a'
down_revision = '1eba2a35a275'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_benchmark_workflowId'), 'benchmark', ['workflowId'], unique=False)
    op.drop_constraint('benchmark_workflowId_fkey', 'benchmark', type_='foreignkey')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key('benchmark_workflowId_fkey', 'benchmark', 'pipeline', ['workflowId'], ['workflowId'])
    op.drop_index(op.f('ix_benchmark_workflowId'), table_name='benchmark')
    # ### end Alembic commands ###