"""Grava e consulta os registros de auditoria enviados pelos serviços (RF12, RNF16)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.excecoes import RegraDeNegocioViolada
from app.core.paginacao import Paginacao
from app.models import LogRequisicao


class RegistroRequisicao(BaseModel):
    """Só estes campos são aceitos; qualquer outro vindo na mensagem é descartado."""

    model_config = ConfigDict(extra="ignore")

    correlation_id: str = Field(min_length=1, max_length=64)
    usuario_id: int | None = None
    rota: str = Field(max_length=300)
    metodo_http: str = Field(max_length=10)
    status_http: int = Field(ge=100, le=599)
    ip_origem: str = Field(max_length=45)
    tempo_resposta_ms: int = Field(ge=0)
    timestamp: datetime


def gravar_registro(db: Session, dados: dict) -> bool:
    """Grava um registro. Devolve False se o correlation_id já estava gravado.

    O RabbitMQ pode entregar a mesma mensagem mais de uma vez; o `correlation_id` único
    torna a gravação idempotente.
    """
    registro = RegistroRequisicao.model_validate(dados)
    db.add(LogRequisicao(**registro.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


CAMPOS_ORDENAVEIS = {"id", "timestamp", "status_http", "tempo_resposta_ms"}


def listar_registros(
    db: Session,
    pagina: Paginacao,
    *,
    usuario_id: int | None = None,
    status_http: int | None = None,
    classe_status: int | None = None,
    metodo_http: str | None = None,
    busca: str | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
) -> tuple[list[LogRequisicao], int]:
    """Lista a trilha de auditoria com filtros. `classe_status` 2, 4 ou 5 filtra 2xx, 4xx, 5xx."""
    if pagina.ordenar_por not in CAMPOS_ORDENAVEIS:
        raise RegraDeNegocioViolada(
            f"Não é possível ordenar por '{pagina.ordenar_por}'. "
            f"Use: {', '.join(sorted(CAMPOS_ORDENAVEIS))}.",
            codigo="ORDENACAO_INVALIDA",
        )
    condicoes = []
    if usuario_id is not None:
        condicoes.append(LogRequisicao.usuario_id == usuario_id)
    if status_http is not None:
        condicoes.append(LogRequisicao.status_http == status_http)
    if classe_status is not None:
        condicoes.append(
            LogRequisicao.status_http.between(classe_status * 100, classe_status * 100 + 99)
        )
    if metodo_http:
        condicoes.append(LogRequisicao.metodo_http == metodo_http.upper())
    if busca:
        termo = f"%{busca}%"
        condicoes.append(
            or_(LogRequisicao.rota.ilike(termo), LogRequisicao.correlation_id.ilike(termo))
        )
    if desde is not None:
        condicoes.append(LogRequisicao.timestamp >= desde)
    if ate is not None:
        condicoes.append(LogRequisicao.timestamp <= ate)

    total = db.scalar(select(func.count()).select_from(LogRequisicao).where(*condicoes)) or 0
    coluna = getattr(LogRequisicao, pagina.ordenar_por)
    ordem = coluna.desc() if pagina.ordem == "desc" else coluna.asc()
    itens = db.scalars(
        select(LogRequisicao)
        .where(*condicoes)
        .order_by(ordem, LogRequisicao.id)
        .offset(pagina.deslocamento)
        .limit(pagina.limite)
    ).all()
    return list(itens), total
