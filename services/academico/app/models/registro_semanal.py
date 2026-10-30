from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.inscricao import Inscricao


class RegistroSemanal(Base):
    """Presença e entrega de atividades de uma inscrição em uma semana (RF07).

    Alimenta o sinal de abandono silencioso. A semana é identificada pela segunda-feira.
    """

    __tablename__ = "registro_semanal"
    __table_args__ = (
        UniqueConstraint("inscricao_id", "semana_inicio"),
        CheckConstraint("atividades_previstas >= 0", name="previstas_nao_negativas"),
        CheckConstraint(
            "atividades_entregues >= 0 AND atividades_entregues <= atividades_previstas",
            name="entregues_validas",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inscricao_id: Mapped[int] = mapped_column(
        ForeignKey("inscricao.id", ondelete="RESTRICT"), index=True
    )
    semana_inicio: Mapped[date] = mapped_column(Date)
    presente: Mapped[bool]
    atividades_previstas: Mapped[int] = mapped_column(default=0, server_default="0")
    atividades_entregues: Mapped[int] = mapped_column(default=0, server_default="0")

    inscricao: Mapped[Inscricao] = relationship(back_populates="semanas")
