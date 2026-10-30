"""cria atendimento_alerta e acompanhamento

Revision ID: 7a1c2e9b5d40
Revises: 4cb24d9aea17
Create Date: 2026-10-30 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1c2e9b5d40'
down_revision: Union[str, Sequence[str], None] = '4cb24d9aea17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('atendimento_alerta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('disciplina_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=15), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('nivel', sa.String(length=10), nullable=False),
    sa.Column('atualizado_por', sa.Integer(), nullable=True),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("tipo IN ('queda', 'frequencia')", name=op.f('ck_atendimento_alerta_tipo_valido')),
    sa.CheckConstraint("estado IN ('pendente', 'acomp', 'encerrado')", name=op.f('ck_atendimento_alerta_estado_valido')),
    sa.CheckConstraint("nivel IN ('atencao', 'alto')", name=op.f('ck_atendimento_alerta_nivel_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_atendimento_alerta')),
    sa.UniqueConstraint('aluno_id', 'tipo', 'disciplina_id', name=op.f('uq_atendimento_alerta_aluno_id_tipo_disciplina_id'))
    )
    op.create_index(op.f('ix_atendimento_alerta_aluno_id'), 'atendimento_alerta', ['aluno_id'], unique=False)
    op.create_table('acompanhamento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('aluno_id', sa.Integer(), nullable=False),
    sa.Column('disciplina_id', sa.Integer(), nullable=True),
    sa.Column('tipo', sa.String(length=15), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('responsavel', sa.String(length=60), nullable=False),
    sa.Column('responsavel_id', sa.Integer(), nullable=True),
    sa.Column('observacao', sa.String(length=200), nullable=False),
    sa.Column('revisao', sa.Date(), nullable=True),
    sa.Column('revisao_feita', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('visivel_ao_aluno', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("tipo IN ('contato', 'orientacao', 'monitoria')", name=op.f('ck_acompanhamento_tipo_valido')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_acompanhamento'))
    )
    op.create_index(op.f('ix_acompanhamento_aluno_id'), 'acompanhamento', ['aluno_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_acompanhamento_aluno_id'), table_name='acompanhamento')
    op.drop_table('acompanhamento')
    op.drop_index(op.f('ix_atendimento_alerta_aluno_id'), table_name='atendimento_alerta')
    op.drop_table('atendimento_alerta')
