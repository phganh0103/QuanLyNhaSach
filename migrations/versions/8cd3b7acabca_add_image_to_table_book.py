"""add image to table book

Revision ID: 8cd3b7acabca
Revises: 673aa64787b2
Create Date: 2024-12-09 12:22:01.334557

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8cd3b7acabca'
down_revision = '673aa64787b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('book', schema=None) as batch_op:
        batch_op.drop_column('image')

    # ### end Alembic commands ###