"""Rotas do aluno (o próprio desempenho e pedidos de apoio) e da coordenação (atendimento).

O aluno só enxerga o que é dele: o `aluno_id` vem do token, nunca da requisição.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.database import get_db
from app.core.excecoes import AcessoNegado
from app.core.respostas import Resposta
from app.core.seguranca import AlunoAtual, UsuarioAtual, aluno_atual, usuario_atual
from app.schemas.analitico import Painel
from app.schemas.apoio import (
    EstadoApoio,
    EstadoEntrada,
    PassoHistorico,
    SolicitacaoDaCoordenacao,
    SolicitacaoEntrada,
    SolicitacaoSaida,
)
from app.services import apoio
from app.services.painel import montar_painel

Sessao = Annotated[Session, Depends(get_db)]
Aluno = Annotated[AlunoAtual, Depends(aluno_atual)]


def gestor(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
    if usuario.role not in {"admin", "coordenador"}:
        raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
    return usuario


Gestor = Annotated[UsuarioAtual, Depends(gestor)]

meu = APIRouter(prefix="/meu", tags=["Aluno"])
atendimento = APIRouter(prefix="/apoio", tags=["Apoio"])


def _saida(db: Session, pedido) -> SolicitacaoSaida:
    base = SolicitacaoSaida.model_validate(pedido)
    historico = [PassoHistorico.model_validate(h) for h in apoio.historico_de(db, pedido.id)]
    return base.model_copy(update={"historico": historico})


@meu.get("/painel", response_model=Resposta[Painel])
def meu_painel(aluno: Aluno):
    """Notas, frequência e situação do próprio aluno, no mesmo formato do painel."""
    inscricoes = academico.buscar_inscricoes(aluno_id=aluno.aluno_id)
    return Resposta[Painel](dados=montar_painel(inscricoes))


@meu.post("/apoio", response_model=Resposta[SolicitacaoSaida], status_code=status.HTTP_201_CREATED)
def solicitar_apoio(dados: SolicitacaoEntrada, db: Sessao, aluno: Aluno):
    """Envia um pedido de apoio à coordenação. No máximo 5 em aberto por aluno."""
    pedido = apoio.solicitar(db, aluno, dados)
    return Resposta[SolicitacaoSaida](dados=_saida(db, pedido), mensagem="Solicitação enviada.")


@meu.get("/apoio", response_model=Resposta[list[SolicitacaoSaida]])
def meus_pedidos(db: Sessao, aluno: Aluno):
    pedidos = apoio.do_aluno(db, aluno.aluno_id)
    return Resposta[list[SolicitacaoSaida]](dados=[_saida(db, p) for p in pedidos])


@atendimento.get("", response_model=Resposta[list[SolicitacaoDaCoordenacao]])
def listar_pedidos(db: Sessao, _: Gestor, estado: EstadoApoio | None = None):
    """Pedidos de apoio recebidos, mais recentes primeiro, com quem pediu."""
    pedidos = apoio.listar(db, estado)
    alunos: dict[int, tuple[str, str, dict[int, str]]] = {}
    for aluno_id in {p.aluno_id for p in pedidos}:
        inscricoes = academico.buscar_inscricoes(aluno_id=aluno_id)
        if inscricoes:
            aluno = inscricoes[0].aluno
            disciplinas = {i.disciplina.id: i.disciplina.nome for i in inscricoes}
            alunos[aluno_id] = (aluno.nome_completo, aluno.matricula, disciplinas)
    saida = []
    for pedido in pedidos:
        nome, matricula, disciplinas = alunos.get(pedido.aluno_id, (None, None, {}))
        base = _saida(db, pedido)
        saida.append(
            SolicitacaoDaCoordenacao(
                **base.model_dump(),
                aluno_nome=nome,
                matricula=matricula,
                disciplina_nome=disciplinas.get(pedido.disciplina_id),
            )
        )
    return Resposta[list[SolicitacaoDaCoordenacao]](dados=saida)


@atendimento.put("/{solicitacao_id}/estado", response_model=Resposta[SolicitacaoSaida])
def mudar_estado(solicitacao_id: int, dados: EstadoEntrada, db: Sessao, usuario: Gestor):
    pedido = apoio.mudar_estado(db, solicitacao_id, dados.estado, usuario)
    return Resposta[SolicitacaoSaida](dados=_saida(db, pedido), mensagem="Estado atualizado.")
