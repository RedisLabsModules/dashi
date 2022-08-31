"""empty message

Revision ID: c66db7eebd3b
Revises: d592a633bee4
Create Date: 2022-08-15 00:00:06.642853

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c66db7eebd3b'
down_revision = 'd592a633bee4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_pipeline_pipelineId', table_name='pipeline')
    op.create_index(op.f('ix_pipeline_pipelineId'), 'pipeline', ['pipelineId'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_pipeline_pipelineId'), table_name='pipeline')
    op.create_index('ix_pipeline_pipelineId', 'pipeline', ['pipelineId'], unique=False)
    # ### end Alembic commands ###