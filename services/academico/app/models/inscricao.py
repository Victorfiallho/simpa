from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.aluno import Aluno
from app.models.disciplina import Disciplina
from app.models.turma import opcoes_sql

STATUS_INSCRICAO = ("ativa", "trancada", "concluida", "cancelada")


class Inscricao(Base):
    """Liga o aluno a cada disciplina que ele cursa (D01). Notas e frequência ficam aqui."""

    __tablename__ = "inscricao"
    __table_args__ = (
        UniqueConstraint("aluno_id", "disciplina_id"),
        CheckConstraint(opcoes_sql("status", STATUS_INSCRICAO), name="status_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id", ondelete="RESTRICT"), index=True)
    disciplina_id: Mapped[int] = mapped_column(
        ForeignKey("disciplina.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(12), default="ativa", server_default="ativa")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    aluno: Mapped[Aluno] = relationship(back_populates="inscricoes")
    disciplina: Mapped[Disciplina] = relationship(lazy="joined")
    avaliacoes: Mapped[list["Avaliacao"]] = relationship(  # noqa: F821
        back_populates="inscricao", order_by="Avaliacao.id"
    )
    frequencias: Mapped[list["Frequencia"]] = relationship(  # noqa: F821
        back_populates="inscricao", order_by="Frequencia.id"
    )
