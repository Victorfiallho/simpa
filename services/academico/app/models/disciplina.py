from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.turma import STATUS_TURMA, Turma, opcoes_sql

STATUS_DISCIPLINA = STATUS_TURMA


class Disciplina(Base):
    """Oferta de uma disciplina em um período letivo, ligada à turma de origem (D01)."""

    __tablename__ = "disciplina"
    __table_args__ = (
        CheckConstraint(opcoes_sql("status", STATUS_DISCIPLINA), name="status_valido"),
        CheckConstraint("carga_horaria > 0", name="carga_horaria_positiva"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    carga_horaria: Mapped[int]
    periodo_letivo: Mapped[str] = mapped_column(String(10), index=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="RESTRICT"), index=True)
    # Id de um Usuario do serviço auth. Não é FK: o usuário mora em outro banco (D13).
    professor_id: Mapped[int | None] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(12), default="ativa", server_default="ativa")

    turma: Mapped[Turma] = relationship(lazy="joined")

    @property
    def encerrada(self) -> bool:
        """Encerrar a turma também encerra as disciplinas dela (D10)."""
        return self.status == "encerrada" or self.turma.status == "encerrada"
