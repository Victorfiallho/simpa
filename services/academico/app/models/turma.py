from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

STATUS_TURMA = ("ativa", "inativa", "encerrada")
TURNOS = ("matutino", "vespertino", "noturno", "integral")


def opcoes_sql(coluna: str, valores: tuple[str, ...]) -> str:
    """Monta a expressão de CHECK `coluna IN ('a', 'b')`."""
    return f"{coluna} IN ({', '.join(repr(v) for v in valores)})"


class Turma(Base):
    """Agrupamento/coorte de alunos, ex.: "IA – 2º período – Noturno" (D01)."""

    __tablename__ = "turma"
    __table_args__ = (
        CheckConstraint(opcoes_sql("status", STATUS_TURMA), name="status_valido"),
        CheckConstraint(opcoes_sql("turno", TURNOS), name="turno_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    curso: Mapped[str] = mapped_column(String(120))
    periodo_letivo: Mapped[str] = mapped_column(String(10), index=True)
    turno: Mapped[str] = mapped_column(String(12))
    sala: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(12), default="ativa", server_default="ativa")
