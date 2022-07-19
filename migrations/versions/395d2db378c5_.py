"""empty message

Revision ID: 395d2db378c5
Revises: 
Create Date: 2022-07-18 17:04:26.943715

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '395d2db378c5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('pipeline',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=30), nullable=True),
    sa.Column('pipelineId', sa.Integer(), nullable=True, unique=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('workflow',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workflowId', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('workflow')
    op.drop_table('pipeline')
    # ### end Alembic commands ###
