"""Eventos já tratados pelo worker (idempotência, D14).

O broker entrega "pelo menos uma vez": o mesmo evento pode chegar de novo (queda entre o envio e a
marcação no acadêmico, mensagem devolvida depois de uma falha). O worker anota o `event_id` aqui
e ignora repetições.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _agora() -> datetime:
    return datetime.now(UTC)


class EventoProcessado(Base):
    __tablename__ = "evento_processado"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    processado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
