from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ESTADOS_APOIO = ("recebida", "atendimento", "concluida")
MOTIVOS_APOIO = (
    "Dificuldade com o conteúdo",
    "Notas abaixo do esperado",
    "Muitas faltas ou frequência baixa",
    "Questão pessoal ou de saúde",
    "Outro motivo",
)


class SolicitacaoApoio(Base):
    """Pedido de ajuda que o aluno envia à coordenação (RF07)."""

    __tablename__ = "solicitacao_apoio"
    __table_args__ = (
        CheckConstraint(
            f"estado IN ({', '.join(repr(e) for e in ESTADOS_APOIO)})", name="estado_valido"
        ),
        # Pedidos do aluno, do mais recente (e a contagem dos abertos dele).
        Index("ix_solicitacao_apoio_aluno_id_id", "aluno_id", "id"),
        # Fila da coordenação por estado, do mais recente.
        Index("ix_solicitacao_apoio_estado_id", "estado", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Ids do serviço acadêmico (sem FK: outro banco, D13).
    aluno_id: Mapped[int]
    # Nulo = pedido geral, sobre nenhuma disciplina específica.
    disciplina_id: Mapped[int | None]
    motivo: Mapped[str] = mapped_column(String(60))
    texto: Mapped[str] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(15), default="recebida")
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HistoricoApoio(Base):
    """Cada mudança de estado de uma solicitação, para o aluno acompanhar."""

    __tablename__ = "historico_apoio"
    # Atende o histórico de uma solicitação, em ordem: WHERE solicitacao_id ORDER BY id.
    __table_args__ = (Index("ix_historico_apoio_solicitacao_id_id", "solicitacao_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    solicitacao_id: Mapped[int] = mapped_column(
        ForeignKey("solicitacao_apoio.id", ondelete="RESTRICT")
    )
    estado: Mapped[str] = mapped_column(String(15))
    alterado_por: Mapped[int | None]
    em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
