"""cria evento_processado (idempotência do consumidor de eventos)

Revision ID: b6d8f0a2c4e3
Revises: 9c3e5a7b1d86
Create Date: 2026-11-10 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d8f0a2c4e3'
down_revision: Union[str, Sequence[str], None] = '9c3e5a7b1d86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('evento_processado',
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('processado_em', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('event_id', name=op.f('pk_evento_processado'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('evento_processado')
