"""aceita o tipo de alerta 'abandono' em atendimento_alerta

Revision ID: 8b2d4f6a1c75
Revises: 7a1c2e9b5d40
Create Date: 2026-10-30 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8b2d4f6a1c75'
down_revision: Union[str, Sequence[str], None] = '7a1c2e9b5d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('ck_atendimento_alerta_tipo_valido'), 'atendimento_alerta', type_='check')
    op.create_check_constraint(
        op.f('ck_atendimento_alerta_tipo_valido'),
        'atendimento_alerta',
        "tipo IN ('queda', 'frequencia', 'abandono')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM atendimento_alerta WHERE tipo = 'abandono'")
    op.drop_constraint(op.f('ck_atendimento_alerta_tipo_valido'), 'atendimento_alerta', type_='check')
    op.create_check_constraint(
        op.f('ck_atendimento_alerta_tipo_valido'),
        'atendimento_alerta',
        "tipo IN ('queda', 'frequencia')",
    )
