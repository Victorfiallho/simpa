"""cria registro_semanal

Revision ID: f7b9d1e35a64
Revises: 38c995d14063
Create Date: 2026-10-30 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b9d1e35a64'
down_revision: Union[str, Sequence[str], None] = '38c995d14063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('registro_semanal',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('inscricao_id', sa.Integer(), nullable=False),
    sa.Column('semana_inicio', sa.Date(), nullable=False),
    sa.Column('presente', sa.Boolean(), nullable=False),
    sa.Column('atividades_previstas', sa.Integer(), server_default='0', nullable=False),
    sa.Column('atividades_entregues', sa.Integer(), server_default='0', nullable=False),
    sa.CheckConstraint('atividades_previstas >= 0', name=op.f('ck_registro_semanal_previstas_nao_negativas')),
    sa.CheckConstraint('atividades_entregues >= 0 AND atividades_entregues <= atividades_previstas', name=op.f('ck_registro_semanal_entregues_validas')),
    sa.ForeignKeyConstraint(['inscricao_id'], ['inscricao.id'], name=op.f('fk_registro_semanal_inscricao_id_inscricao'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_registro_semanal')),
    sa.UniqueConstraint('inscricao_id', 'semana_inicio', name=op.f('uq_registro_semanal_inscricao_id_semana_inicio'))
    )
    op.create_index(op.f('ix_registro_semanal_inscricao_id'), 'registro_semanal', ['inscricao_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_registro_semanal_inscricao_id'), table_name='registro_semanal')
    op.drop_table('registro_semanal')
