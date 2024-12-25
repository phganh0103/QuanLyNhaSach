"""add duration field to table book

Revision ID: 0c6850089177
Revises: 6a01c1577edf
Create Date: 2024-12-09 17:39:09.260841

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0c6850089177'
down_revision = '6a01c1577edf'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration', sa.Float(), nullable=False))
        batch_op.drop_column('Pages')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.add_column(sa.Column('Pages', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.drop_column('duration')

    # ### end Alembic commands ###