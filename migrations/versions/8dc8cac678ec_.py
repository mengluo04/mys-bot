"""empty message

迁移 ID: 8dc8cac678ec
父迁移: 367c41acf90c
创建时间: 2024-10-30 21:16:45.769408

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '8dc8cac678ec'
down_revision: str | Sequence[str] | None = '367c41acf90c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('nonebot_plugin_user_bind_userbind',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bot_id', sa.String(length=64), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('uid', sa.String(length=64), nullable=False),
    sa.Column('game', sa.String(length=64), nullable=False),
    sa.Column('region', sa.String(length=64), nullable=False),
    sa.Column('mys_id', sa.String(length=64), nullable=True),
    sa.Column('device_id', sa.String(length=64), nullable=True),
    sa.Column('device_fp', sa.String(length=64), nullable=True),
    sa.Column('cookie', sa.TEXT(), nullable=True),
    sa.Column('stoken', sa.TEXT(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_nonebot_plugin_user_bind_userbind')),
    info={'bind_key': 'nonebot_plugin_user_bind'}
    )
    op.drop_table('user_bind_userbind')
    # ### end Alembic commands ###


def downgrade(name: str = "") -> None:
    if name:
        return
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_bind_userbind',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('bot_id', sa.VARCHAR(length=64), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=64), nullable=False),
    sa.Column('uid', sa.VARCHAR(length=64), nullable=False),
    sa.Column('game', sa.VARCHAR(length=64), nullable=False),
    sa.Column('mys_id', sa.VARCHAR(length=64), nullable=True),
    sa.Column('device_id', sa.VARCHAR(length=64), nullable=True),
    sa.Column('device_fp', sa.VARCHAR(length=64), nullable=True),
    sa.Column('cookie', sa.TEXT(), nullable=True),
    sa.Column('stoken', sa.TEXT(), nullable=True),
    sa.Column('region', sa.VARCHAR(length=64), nullable=False),
    sa.PrimaryKeyConstraint('id', name='pk_user_bind_userbind')
    )
    op.drop_table('nonebot_plugin_user_bind_userbind')
    # ### end Alembic commands ###
