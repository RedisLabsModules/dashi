"""empty message

Revision ID: fe108f427881
Revises: 54aac1f43e71
Create Date: 2023-06-15 03:59:16.892700

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe108f427881'
down_revision = '54aac1f43e71'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('pipeline_statuses', sa.Column('workflow_run_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_pipeline_statuses_workflow_run_id'), 'pipeline_statuses', ['workflow_run_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_pipeline_statuses_workflow_run_id'), table_name='pipeline_statuses')
    op.drop_column('pipeline_statuses', 'workflow_run_id')
    # ### end Alembic commands ###
