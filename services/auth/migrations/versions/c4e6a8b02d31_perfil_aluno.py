"""perfil aluno: usuario.aluno_id e role 'aluno'

Revision ID: c4e6a8b02d31
Revises: 8223395c194d
Create Date: 2026-10-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e6a8b02d31'
down_revision: Union[str, Sequence[str], None] = '8223395c194d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuario', sa.Column('aluno_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(op.f('uq_usuario_aluno_id'), 'usuario', ['aluno_id'])
    op.drop_constraint(op.f('ck_usuario_role_valida'), 'usuario', type_='check')
    op.create_check_constraint(
        op.f('ck_usuario_role_valida'),
        'usuario',
        "role IN ('admin', 'coordenador', 'professor', 'aluno')",
    )
    op.create_check_constraint(
        op.f('ck_usuario_aluno_com_cadastro'),
        'usuario',
        "(role = 'aluno') = (aluno_id IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('ck_usuario_aluno_com_cadastro'), 'usuario', type_='check')
    op.drop_constraint(op.f('ck_usuario_role_valida'), 'usuario', type_='check')
    op.create_check_constraint(
        op.f('ck_usuario_role_valida'),
        'usuario',
        "role IN ('admin', 'coordenador', 'professor')",
    )
    op.drop_constraint(op.f('uq_usuario_aluno_id'), 'usuario', type_='unique')
    op.drop_column('usuario', 'aluno_id')
