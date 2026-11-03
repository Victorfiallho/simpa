"""indices das consultas do analitico

Troca índices de uma coluna por compostos que atendem filtro + ordenação das consultas reais
(ver models), e remove um índice redundante da UNIQUE de atendimento_alerta. Em cada troca o
índice novo é criado antes de o antigo cair.

Revision ID: 9c3e5a7b1d86
Revises: d5f7b9c13e42
Create Date: 2026-11-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9c3e5a7b1d86'
down_revision: Union[str, Sequence[str], None] = 'd5f7b9c13e42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_resultado_risco_inscricao_id_id', 'resultado_risco', ['inscricao_id', 'id'], unique=False)
    op.drop_index(op.f('ix_resultado_risco_inscricao_id'), table_name='resultado_risco')

    op.create_index('ix_acompanhamento_aluno_id_data_id', 'acompanhamento', ['aluno_id', 'data', 'id'], unique=False)
    op.drop_index(op.f('ix_acompanhamento_aluno_id'), table_name='acompanhamento')

    op.create_index('ix_solicitacao_apoio_aluno_id_id', 'solicitacao_apoio', ['aluno_id', 'id'], unique=False)
    op.create_index('ix_solicitacao_apoio_estado_id', 'solicitacao_apoio', ['estado', 'id'], unique=False)
    op.drop_index(op.f('ix_solicitacao_apoio_aluno_id'), table_name='solicitacao_apoio')
    op.drop_index(op.f('ix_solicitacao_apoio_estado'), table_name='solicitacao_apoio')

    op.create_index('ix_historico_apoio_solicitacao_id_id', 'historico_apoio', ['solicitacao_id', 'id'], unique=False)
    op.drop_index(op.f('ix_historico_apoio_solicitacao_id'), table_name='historico_apoio')

    # A UNIQUE (aluno_id, tipo, disciplina_id) já atende a busca só por aluno_id.
    op.drop_index(op.f('ix_atendimento_alerta_aluno_id'), table_name='atendimento_alerta')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(op.f('ix_atendimento_alerta_aluno_id'), 'atendimento_alerta', ['aluno_id'], unique=False)

    op.create_index(op.f('ix_historico_apoio_solicitacao_id'), 'historico_apoio', ['solicitacao_id'], unique=False)
    op.drop_index('ix_historico_apoio_solicitacao_id_id', table_name='historico_apoio')

    op.create_index(op.f('ix_solicitacao_apoio_aluno_id'), 'solicitacao_apoio', ['aluno_id'], unique=False)
    op.create_index(op.f('ix_solicitacao_apoio_estado'), 'solicitacao_apoio', ['estado'], unique=False)
    op.drop_index('ix_solicitacao_apoio_estado_id', table_name='solicitacao_apoio')
    op.drop_index('ix_solicitacao_apoio_aluno_id_id', table_name='solicitacao_apoio')

    op.create_index(op.f('ix_acompanhamento_aluno_id'), 'acompanhamento', ['aluno_id'], unique=False)
    op.drop_index('ix_acompanhamento_aluno_id_data_id', table_name='acompanhamento')

    op.create_index(op.f('ix_resultado_risco_inscricao_id'), 'resultado_risco', ['inscricao_id'], unique=False)
    op.drop_index('ix_resultado_risco_inscricao_id_id', table_name='resultado_risco')
