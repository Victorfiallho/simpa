"""Solicitações de apoio do aluno à coordenação (RF07).

O aluno pede ajuda (motivo + texto curto, opcionalmente sobre uma disciplina) e acompanha o
estado: recebida, em atendimento, concluída. A coordenação atende e muda o estado.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.excecoes import Conflito, RecursoNaoEncontrado, RegraDeNegocioViolada
from app.core.seguranca import AlunoAtual, UsuarioAtual
from app.models import HistoricoApoio, SolicitacaoApoio
from app.models.apoio import MOTIVOS_APOIO
from app.schemas.apoio import SolicitacaoEntrada

LIMITE_EM_ABERTO = 5


def solicitar(db: Session, aluno: AlunoAtual, dados: SolicitacaoEntrada) -> SolicitacaoApoio:
    if dados.motivo not in MOTIVOS_APOIO:
        raise RegraDeNegocioViolada("Selecione um dos motivos da lista.", codigo="MOTIVO_INVALIDO")
    if dados.disciplina_id is not None:
        inscricoes = academico.buscar_inscricoes(aluno_id=aluno.aluno_id)
        if not any(i.disciplina.id == dados.disciplina_id for i in inscricoes):
            raise RegraDeNegocioViolada(
                "Selecione uma disciplina em que você está inscrito.",
                codigo="DISCIPLINA_NAO_INSCRITA",
            )
    abertas = db.scalar(
        select(func.count())
        .select_from(SolicitacaoApoio)
        .where(SolicitacaoApoio.aluno_id == aluno.aluno_id, SolicitacaoApoio.estado != "concluida")
    )
    if (abertas or 0) >= LIMITE_EM_ABERTO:
        raise Conflito(
            f"Você já tem {LIMITE_EM_ABERTO} pedidos em aberto; aguarde o atendimento.",
            codigo="LIMITE_DE_SOLICITACOES",
        )
    pedido = SolicitacaoApoio(
        aluno_id=aluno.aluno_id,
        disciplina_id=dados.disciplina_id,
        motivo=dados.motivo,
        texto=dados.texto,
        estado="recebida",
    )
    db.add(pedido)
    db.flush()
    db.add(HistoricoApoio(solicitacao_id=pedido.id, estado="recebida", alterado_por=aluno.id))
    db.commit()
    db.refresh(pedido)
    return pedido


def historico_de(db: Session, solicitacao_id: int) -> list[HistoricoApoio]:
    consulta = (
        select(HistoricoApoio)
        .where(HistoricoApoio.solicitacao_id == solicitacao_id)
        .order_by(HistoricoApoio.id)
    )
    return list(db.scalars(consulta))


def do_aluno(db: Session, aluno_id: int) -> list[SolicitacaoApoio]:
    consulta = (
        select(SolicitacaoApoio)
        .where(SolicitacaoApoio.aluno_id == aluno_id)
        .order_by(SolicitacaoApoio.id.desc())
    )
    return list(db.scalars(consulta))


def listar(db: Session, estado: str | None = None) -> list[SolicitacaoApoio]:
    """Para a coordenação: mais recentes primeiro."""
    consulta = select(SolicitacaoApoio).order_by(SolicitacaoApoio.id.desc())
    if estado is not None:
        consulta = consulta.where(SolicitacaoApoio.estado == estado)
    return list(db.scalars(consulta))


def mudar_estado(
    db: Session, solicitacao_id: int, estado: str, usuario: UsuarioAtual
) -> SolicitacaoApoio:
    pedido = db.get(SolicitacaoApoio, solicitacao_id)
    if pedido is None:
        raise RecursoNaoEncontrado(f"Solicitação {solicitacao_id} não encontrada.")
    if pedido.estado != estado:
        pedido.estado = estado
        db.add(HistoricoApoio(solicitacao_id=pedido.id, estado=estado, alterado_por=usuario.id))
        db.commit()
        db.refresh(pedido)
    return pedido
