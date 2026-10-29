from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.inscricao import Inscricao
from app.models.turma import opcoes_sql

TIPOS_AVALIACAO = ("prova", "trabalho", "atividade", "projeto", "seminario")


class Avaliacao(Base):
    """Uma nota lançada para uma inscrição (D02). Numeric, nunca float (D06)."""

    __tablename__ = "avaliacao"
    __table_args__ = (
        CheckConstraint("nota >= 0 AND nota <= 10", name="nota_entre_0_e_10"),
        CheckConstraint("peso > 0", name="peso_positivo"),
        CheckConstraint(opcoes_sql("tipo_avaliacao", TIPOS_AVALIACAO), name="tipo_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inscricao_id: Mapped[int] = mapped_column(
        ForeignKey("inscricao.id", ondelete="RESTRICT"), index=True
    )
    tipo_avaliacao: Mapped[str] = mapped_column(String(20))
    periodo_avaliacao: Mapped[str] = mapped_column(String(10))
    nota: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    peso: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    inscricao: Mapped[Inscricao] = relationship(back_populates="avaliacoes")
