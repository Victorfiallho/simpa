from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.turma import opcoes_sql

STATUS_ALUNO = ("ativo", "inativo", "transferido", "concluido", "evadido")


class Aluno(Base):
    __tablename__ = "aluno"
    __table_args__ = (CheckConstraint(opcoes_sql("status", STATUS_ALUNO), name="status_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)
    nome_completo: Mapped[str] = mapped_column(String(150), index=True)
    # Só os 11 dígitos. Único, mas opcional (vários alunos podem não ter CPF cadastrado).
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(20))
    data_nascimento: Mapped[date | None]
    curso: Mapped[str] = mapped_column(String(120))
    # Turma de origem; as disciplinas cursadas vêm das inscrições (D01).
    turma_id: Mapped[int] = mapped_column(ForeignKey("turma.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="ativo", server_default="ativo")

    inscricoes: Mapped[list["Inscricao"]] = relationship(  # noqa: F821
        back_populates="aluno", order_by="Inscricao.id"
    )
