from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

TIPOS_ALERTA = ("queda", "frequencia")
ESTADOS_ATENDIMENTO = ("pendente", "acomp", "encerrado")
TIPOS_ACOMPANHAMENTO = ("contato", "orientacao", "monitoria")
NIVEIS = ("atencao", "alto")


def _em(valores: tuple[str, ...]) -> str:
    return ", ".join(repr(v) for v in valores)


class AtendimentoAlerta(Base):
    """Situação do atendimento de um alerta (pendente, em acompanhamento, encerrado).

    Os alertas em si são sempre calculados na hora (dados derivados); só o que a coordenação
    decidiu sobre eles é gravado. `nivel` guarda a gravidade no momento da decisão: se o alerta
    piorar depois, ele volta a aparecer como pendente.
    """

    __tablename__ = "atendimento_alerta"
    __table_args__ = (
        UniqueConstraint("aluno_id", "tipo", "disciplina_id"),
        CheckConstraint(f"tipo IN ({_em(TIPOS_ALERTA)})", name="tipo_valido"),
        CheckConstraint(f"estado IN ({_em(ESTADOS_ATENDIMENTO)})", name="estado_valido"),
        CheckConstraint(f"nivel IN ({_em(NIVEIS)})", name="nivel_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Ids do serviço acadêmico. Não são FK: moram em outro banco (D13).
    aluno_id: Mapped[int] = mapped_column(index=True)
    disciplina_id: Mapped[int]
    tipo: Mapped[str] = mapped_column(String(15))
    estado: Mapped[str] = mapped_column(String(15))
    nivel: Mapped[str] = mapped_column(String(10))
    atualizado_por: Mapped[int | None]
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Acompanhamento(Base):
    """Registro de uma ação da coordenação com o aluno (contato, orientação, monitoria)."""

    __tablename__ = "acompanhamento"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_em(TIPOS_ACOMPANHAMENTO)})", name="tipo_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(index=True)
    # Nulo = acompanhamento geral, de todas as disciplinas.
    disciplina_id: Mapped[int | None]
    tipo: Mapped[str] = mapped_column(String(15))
    data: Mapped[date] = mapped_column(Date)
    responsavel: Mapped[str] = mapped_column(String(60))
    responsavel_id: Mapped[int | None]
    observacao: Mapped[str] = mapped_column(String(200))
    revisao: Mapped[date | None] = mapped_column(Date)
    revisao_feita: Mapped[bool] = mapped_column(default=False, server_default="false")
    visivel_ao_aluno: Mapped[bool] = mapped_column(default=False, server_default="false")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
