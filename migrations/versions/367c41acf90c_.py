"""empty message

迁移 ID: 367c41acf90c
父迁移: 743faca314fe
创建时间: 2024-10-29 21:21:43.462665

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '367c41acf90c'
down_revision: str | Sequence[str] | None = '743faca314fe'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_bind_userbind', schema=None) as batch_op:
        batch_op.add_column(sa.Column('region', sa.String(length=64), nullable=False))

    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_bind_userbind', schema=None) as batch_op:
        batch_op.drop_column('region')

    # ### end Alembic commands ###