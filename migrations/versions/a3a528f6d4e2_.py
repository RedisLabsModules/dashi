"""empty message

Revision ID: a3a528f6d4e2
Revises: b9360710b6bb
Create Date: 2022-12-28 14:29:13.722159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3a528f6d4e2'
down_revision = 'b9360710b6bb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_pipeline_workflowId', table_name='pipeline')
    op.create_index(op.f('ix_pipeline_workflowId'), 'pipeline', ['workflowId'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_pipeline_workflowId'), table_name='pipeline')
    op.create_index('ix_pipeline_workflowId', 'pipeline', ['workflowId'], unique=False)
    # ### end Alembic commands ###
