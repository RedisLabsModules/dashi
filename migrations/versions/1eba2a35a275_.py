"""empty message

Revision ID: 1eba2a35a275
Revises: 6b8211320ded
Create Date: 2022-10-17 14:25:35.333481

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1eba2a35a275'
down_revision = '6b8211320ded'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('benchmark', sa.Column('workflowId', sa.String(), nullable=True))
    op.create_foreign_key(None, 'benchmark', 'pipeline', ['workflowId'], ['workflowId'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'benchmark', type_='foreignkey')
    op.drop_column('benchmark', 'workflowId')
    # ### end Alembic commands ###