"""indices da auditoria

log_requisicao é a tabela que mais cresce (uma linha por requisição) e a trilha é lida do mais
recente para o mais antigo, filtrada por usuário ou por status. O índice só de usuario_id passa
para (usuario_id, timestamp), e entra (status_http, timestamp).

Revision ID: f8a0c2e46b17
Revises: e6a8c0d24f53
Create Date: 2026-11-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f8a0c2e46b17'
down_revision: Union[str, Sequence[str], None] = 'e6a8c0d24f53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_log_requisicao_usuario_id_timestamp', 'log_requisicao', ['usuario_id', 'timestamp'], unique=False)
    op.create_index('ix_log_requisicao_status_http_timestamp', 'log_requisicao', ['status_http', 'timestamp'], unique=False)
    op.drop_index(op.f('ix_log_requisicao_usuario_id'), table_name='log_requisicao')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(op.f('ix_log_requisicao_usuario_id'), 'log_requisicao', ['usuario_id'], unique=False)
    op.drop_index('ix_log_requisicao_status_http_timestamp', table_name='log_requisicao')
    op.drop_index('ix_log_requisicao_usuario_id_timestamp', table_name='log_requisicao')
