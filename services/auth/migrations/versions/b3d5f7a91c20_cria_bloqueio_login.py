"""cria bloqueio_login

Revision ID: b3d5f7a91c20
Revises: 8223395c194d
Create Date: 2026-10-30 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d5f7a91c20'
down_revision: Union[str, Sequence[str], None] = '8223395c194d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('bloqueio_login',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('chave', sa.String(length=64), nullable=False),
    sa.Column('falhas', sa.Integer(), server_default='0', nullable=False),
    sa.Column('bloqueado_ate', sa.DateTime(timezone=True), nullable=True),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bloqueio_login')),
    sa.UniqueConstraint('chave', name=op.f('uq_bloqueio_login_chave'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bloqueio_login')
