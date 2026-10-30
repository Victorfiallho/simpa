"""Rotas de alertas precoces e acompanhamento (RF07).

Só admin e coordenador. O recorte do professor (só as próprias disciplinas) entra junto com o
RBAC do analítico.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.database import get_db
from app.core.excecoes import AcessoNegado, RecursoNaoEncontrado
from app.core.respostas import Resposta
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.schemas.alertas import (
    AcompanhamentoEntrada,
    AcompanhamentoSaida,
    AtendimentoEntrada,
    EstadoAtendimento,
    ListaAlertas,
    NivelAlerta,
    TipoAlerta,
)
from app.services import acompanhamento, alertas

PERFIS = {"admin", "coordenador"}


def gestor(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
    if usuario.role not in PERFIS:
        raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
    return usuario


Gestor = Annotated[UsuarioAtual, Depends(gestor)]
Sessao = Annotated[Session, Depends(get_db)]

alerta = APIRouter(prefix="/alertas", tags=["Alertas"])
acompanhamentos = APIRouter(prefix="/acompanhamentos", tags=["Acompanhamento"])


@alerta.get("", response_model=Resposta[ListaAlertas])
def listar_alertas(
    db: Sessao,
    _: Gestor,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    periodo_letivo: str | None = None,
    tipo: TipoAlerta | None = None,
    nivel: NivelAlerta | None = None,
    estado: EstadoAtendimento | None = None,
):
    """Alertas ativos do recorte, do mais grave ao menos grave, e o resumo por sinal."""
    inscricoes = academico.buscar_inscricoes(
        turma_id=turma_id, disciplina_id=disciplina_id, periodo_letivo=periodo_letivo
    )
    lista = alertas.listar(db, inscricoes, tipo=tipo, nivel=nivel, estado=estado)
    return Resposta[ListaAlertas](dados=lista)


@alerta.put("/atendimento", response_model=Resposta[None])
def definir_atendimento(dados: AtendimentoEntrada, db: Sessao, usuario: Gestor):
    """Muda a situação do atendimento de um alerta que está ativo."""
    inscricoes = academico.buscar_inscricoes(aluno_id=dados.aluno_id)
    ativo = next(
        (
            a
            for a in alertas.montar_alertas(db, inscricoes)
            if (a.tipo, a.disciplina_id) == (dados.tipo, dados.disciplina_id)
        ),
        None,
    )
    if ativo is None:
        raise RecursoNaoEncontrado("Não há alerta ativo com esses dados.")
    alertas.definir_estado(db, ativo, dados.estado, usuario.id)
    return Resposta[None](mensagem="Atendimento atualizado.")


@acompanhamentos.get("", response_model=Resposta[list[AcompanhamentoSaida]])
def listar_acompanhamentos(aluno_id: int, db: Sessao, _: Gestor):
    linhas = acompanhamento.listar_do_aluno(db, aluno_id)
    saida = [
        AcompanhamentoSaida.model_validate(linha).model_copy(
            update={"revisao_vencida": acompanhamento.revisao_vencida(linha)}
        )
        for linha in linhas
    ]
    return Resposta[list[AcompanhamentoSaida]](dados=saida)


@acompanhamentos.post(
    "", response_model=Resposta[AcompanhamentoSaida], status_code=status.HTTP_201_CREATED
)
def registrar_acompanhamento(dados: AcompanhamentoEntrada, db: Sessao, usuario: Gestor):
    """Registra a ação e passa os alertas pendentes do aluno para "em acompanhamento"."""
    registro = acompanhamento.criar(db, dados, usuario)
    saida = AcompanhamentoSaida.model_validate(registro)
    return Resposta[AcompanhamentoSaida](dados=saida, mensagem="Acompanhamento registrado.")


@acompanhamentos.post(
    "/{acompanhamento_id}/revisao-feita", response_model=Resposta[AcompanhamentoSaida]
)
def revisao_feita(acompanhamento_id: int, db: Sessao, _: Gestor):
    registro = acompanhamento.marcar_revisao_feita(db, acompanhamento_id)
    saida = AcompanhamentoSaida.model_validate(registro)
    return Resposta[AcompanhamentoSaida](dados=saida, mensagem="Revisão marcada como feita.")
