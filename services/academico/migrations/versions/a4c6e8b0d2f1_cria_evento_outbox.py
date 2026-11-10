"""cria evento_outbox (padrão outbox para os eventos de domínio)

Revision ID: a4c6e8b0d2f1
Revises: f7b9d1e35a64
Create Date: 2026-11-10 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4c6e8b0d2f1'
down_revision: Union[str, Sequence[str], None] = 'f7b9d1e35a64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('evento_outbox',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('chave', sa.String(length=60), nullable=False),
    sa.Column('corpo', sa.Text(), nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('enviado_em', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tentativas', sa.Integer(), nullable=False),
    sa.Column('proxima_tentativa_em', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ultimo_erro', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evento_outbox'))
    )
    op.create_index('ix_evento_outbox_enviado_em_proxima_tentativa_em', 'evento_outbox', ['enviado_em', 'proxima_tentativa_em'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_evento_outbox_enviado_em_proxima_tentativa_em', table_name='evento_outbox')
    op.drop_table('evento_outbox')
