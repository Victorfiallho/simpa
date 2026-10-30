"""cria perfil_usuario

Revision ID: e6a8c0d24f53
Revises: c4e6a8b02d31
Create Date: 2026-10-30 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a8c0d24f53'
down_revision: Union[str, Sequence[str], None] = 'c4e6a8b02d31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('perfil_usuario',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('nome_completo', sa.String(length=80), nullable=True),
    sa.Column('cargo', sa.String(length=60), nullable=True),
    sa.Column('matricula_funcional', sa.String(length=20), nullable=True),
    sa.Column('nascimento', sa.Date(), nullable=True),
    sa.Column('cpf', sa.String(length=11), nullable=True),
    sa.Column('telefone', sa.String(length=11), nullable=True),
    sa.Column('email_contato', sa.String(length=254), nullable=True),
    sa.Column('cep', sa.String(length=8), nullable=True),
    sa.Column('rua', sa.String(length=100), nullable=True),
    sa.Column('numero', sa.String(length=10), nullable=True),
    sa.Column('complemento', sa.String(length=60), nullable=True),
    sa.Column('bairro', sa.String(length=60), nullable=True),
    sa.Column('cidade', sa.String(length=60), nullable=True),
    sa.Column('uf', sa.String(length=2), nullable=True),
    sa.Column('emergencia_nome', sa.String(length=80), nullable=True),
    sa.Column('emergencia_parentesco', sa.String(length=40), nullable=True),
    sa.Column('emergencia_telefone', sa.String(length=11), nullable=True),
    sa.Column('foto', sa.LargeBinary(), nullable=True),
    sa.Column('foto_tipo', sa.String(length=15), nullable=True),
    sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], name=op.f('fk_perfil_usuario_usuario_id_usuario'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_perfil_usuario')),
    sa.UniqueConstraint('usuario_id', name=op.f('uq_perfil_usuario_usuario_id'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('perfil_usuario')
