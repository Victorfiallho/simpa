from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.inscricao import Inscricao


class Frequencia(Base):
    """Aulas previstas e faltas de uma inscrição em um período (D02).

    O percentual nunca é gravado: é sempre derivado de faltas e aulas previstas.
    """

    __tablename__ = "frequencia"
    __table_args__ = (
        UniqueConstraint("inscricao_id", "periodo_avaliacao"),
        CheckConstraint("aulas_previstas > 0", name="aulas_previstas_positivas"),
        CheckConstraint("faltas >= 0 AND faltas <= aulas_previstas", name="faltas_validas"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inscricao_id: Mapped[int] = mapped_column(
        ForeignKey("inscricao.id", ondelete="RESTRICT"), index=True
    )
    periodo_avaliacao: Mapped[str] = mapped_column(String(10))
    aulas_previstas: Mapped[int]
    faltas: Mapped[int]

    inscricao: Mapped[Inscricao] = relationship(back_populates="frequencias")
