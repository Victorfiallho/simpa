"""Recálculo e histórico do risco por inscrição (RF07, D04, D11).

Chamado pelo worker a cada evento do acadêmico. Uma linha nova de ResultadoRisco só é
gravada quando status, atenção ou critérios mudam em relação à última (D11).
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.database import get_sessionmaker
from app.core.excecoes import RecursoNaoEncontrado
from app.models import ResultadoRisco
from app.services.painel import STATUS_QUE_CONTAM, calcular

logger = logging.getLogger("analitico.risco")


def ultimo_resultado(db: Session, inscricao_id: int) -> ResultadoRisco | None:
    return db.scalar(
        select(ResultadoRisco)
        .where(ResultadoRisco.inscricao_id == inscricao_id)
        .order_by(ResultadoRisco.id.desc())
        .limit(1)
    )


def registrar(db: Session, inscricao: academico.Inscricao) -> ResultadoRisco | None:
    """Grava a classificação atual se ela mudou. Devolve a linha nova, ou None."""
    if inscricao.status not in STATUS_QUE_CONTAM:
        return None
    classificacao = calcular(inscricao).classificacao
    criterios = ",".join(classificacao.criterios)

    ultimo = ultimo_resultado(db, inscricao.id)
    if ultimo is not None and (ultimo.status, ultimo.atencao, ultimo.criterios_violados) == (
        classificacao.status,
        classificacao.atencao,
        criterios,
    ):
        return None

    novo = ResultadoRisco(
        inscricao_id=inscricao.id,
        media_final=classificacao.media,
        frequencia_final=classificacao.frequencia,
        status=classificacao.status,
        atencao=classificacao.atencao,
        criterios_violados=criterios,
        justificativa=classificacao.justificativa,
    )
    db.add(novo)
    db.commit()
    return novo


def recalcular_risco_da_inscricao(inscricao_id: int) -> None:
    try:
        inscricao = academico.buscar_inscricao(inscricao_id)
    except RecursoNaoEncontrado:
        logger.warning("inscricao nao encontrada", extra={"dados": {"inscricao_id": inscricao_id}})
        return

    with get_sessionmaker()() as db:
        novo = registrar(db, inscricao)
    if novo is not None:
        logger.info(
            "classificacao alterada",
            extra={
                "dados": {
                    "inscricao_id": inscricao_id,
                    "status": novo.status,
                    "atencao": novo.atencao,
                    "criterios": novo.criterios_violados,
                }
            },
        )


def historico(db: Session, inscricao_id: int) -> list[ResultadoRisco]:
    """Transições de risco da inscrição, da mais recente para a mais antiga."""
    return list(
        db.scalars(
            select(ResultadoRisco)
            .where(ResultadoRisco.inscricao_id == inscricao_id)
            .order_by(ResultadoRisco.id.desc())
        )
    )
