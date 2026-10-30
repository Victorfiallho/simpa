from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogRequisicao(Base):
    """Auditoria das requisições (RF12). Gravada pelo worker do auth (evento log.requisicao)."""

    __tablename__ = "log_requisicao"

    id: Mapped[int] = mapped_column(primary_key=True)
    correlation_id: Mapped[str] = mapped_column(String(64), unique=True)
    # Nulo quando a requisição é anônima.
    usuario_id: Mapped[int | None] = mapped_column(index=True)
    rota: Mapped[str] = mapped_column(String(300))
    metodo_http: Mapped[str] = mapped_column(String(10))
    status_http: Mapped[int]
    ip_origem: Mapped[str] = mapped_column(String(45))
    tempo_resposta_ms: Mapped[int]
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
