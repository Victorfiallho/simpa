from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STATUS_RISCO = ("em_risco", "sem_risco", "indeterminado")


class ResultadoRisco(Base):
    """Histórico de classificação de risco por inscrição (RF07).

    Uma linha nova só é gravada quando a classificação muda (D11).
    """

    __tablename__ = "resultado_risco"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in STATUS_RISCO)})", name="status_valido"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Id de uma Inscricao do serviço acadêmico. Não é FK: mora em outro banco (D13).
    inscricao_id: Mapped[int] = mapped_column(index=True)
    media_final: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    # Numeric(5, 2): 100,00% tem cinco dígitos (D16).
    frequencia_final: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    status: Mapped[str] = mapped_column(String(15))
    atencao: Mapped[bool] = mapped_column(default=False, server_default="false")
    criterios_violados: Mapped[str] = mapped_column(String(60), default="", server_default="")
    justificativa: Mapped[str] = mapped_column(Text)
    calculado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
