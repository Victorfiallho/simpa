"""cria solicitacao_apoio e historico_apoio

Revision ID: d5f7b9c13e42
Revises: 4cb24d9aea17
Create Date: 2026-10-30 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f7b9c13e42'
down_revision: Union[str, Sequence[str], None] = '4cb24d9aea17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('solicitacao_apoio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('disciplina_id', sa.Integer(), nullable=True),
    sa.Column('motivo', sa.String(length=60), nullable=False),
    sa.Column('texto', sa.String(length=200), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('criada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('atualizada_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("estado IN ('recebida', 'atendimento', 'concluida')", name=op.f('ck_solicitacao_apoio_estado_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_solicitacao_apoio'))
    )
    op.create_index(op.f('ix_solicitacao_apoio_aluno_id'), 'solicitacao_apoio', ['aluno_id'], unique=False)
    op.create_index(op.f('ix_solicitacao_apoio_estado'), 'solicitacao_apoio', ['estado'], unique=False)
    op.create_table('historico_apoio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('solicitacao_id', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('alterado_por', sa.Integer(), nullable=True),
    sa.Column('em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['solicitacao_id'], ['solicitacao_apoio.id'], name=op.f('fk_historico_apoio_solicitacao_id_solicitacao_apoio'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_historico_apoio'))
    )
    op.create_index(op.f('ix_historico_apoio_solicitacao_id'), 'historico_apoio', ['solicitacao_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_historico_apoio_solicitacao_id'), table_name='historico_apoio')
    op.drop_table('historico_apoio')
    op.drop_index(op.f('ix_solicitacao_apoio_estado'), table_name='solicitacao_apoio')
    op.drop_index(op.f('ix_solicitacao_apoio_aluno_id'), table_name='solicitacao_apoio')
    op.drop_table('solicitacao_apoio')
