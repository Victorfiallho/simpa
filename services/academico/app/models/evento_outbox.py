"""Eventos de domínio a publicar (padrão outbox, D14).

O evento é gravado na MESMA transação da alteração que o originou: ou os dois existem, ou
nenhum. Um despachante separado (`app.events.despachante`) publica no RabbitMQ e só marca
`enviado_em` depois que o broker confirma o recebimento.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _agora() -> datetime:
    return datetime.now(UTC)


class EventoOutbox(Base):
    __tablename__ = "evento_outbox"
    __table_args__ = (
        # Atende a busca do despachante: pendentes (enviado_em nulo) já vencidos, do mais antigo.
        Index(
            "ix_evento_outbox_enviado_em_proxima_tentativa_em", "enviado_em", "proxima_tentativa_em"
        ),
    )

    # UUID do evento: viaja no envelope e permite ao consumidor ignorar entregas repetidas.
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chave: Mapped[str] = mapped_column(String(60))
    # Envelope completo em JSON (evento, event_id, request_id, ocorrido_em e dados).
    corpo: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    proxima_tentativa_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    ultimo_erro: Mapped[str | None] = mapped_column(Text, default=None)
