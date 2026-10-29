"""Rotas /internal: só para outros serviços, na rede interna do Docker (D14).

O gateway bloqueia /api/*/internal, então estas rotas não ficam expostas para fora.
"""

from fastapi import APIRouter

from app.api.dependencias import Sessao
from app.core.excecoes import RecursoNaoEncontrado
from app.core.respostas import Resposta, resposta
from app.repositories.academico import InscricaoRepositorio
from app.schemas.inscricao import InscricaoInterna

interna = APIRouter(prefix="/internal", tags=["Interno"], include_in_schema=False)


@interna.get("/inscricoes", response_model=Resposta[list[InscricaoInterna]])
def inscricoes_detalhadas(
    db: Sessao,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    aluno_id: int | None = None,
    periodo_letivo: str | None = None,
):
    """Inscrições de um recorte, para os indicadores e relatórios do analítico."""
    inscricoes = InscricaoRepositorio(db).listar_detalhadas(
        turma_id=turma_id,
        disciplina_id=disciplina_id,
        aluno_id=aluno_id,
        periodo_letivo=periodo_letivo,
    )
    return Resposta[list[InscricaoInterna]](
        dados=[InscricaoInterna.model_validate(i) for i in inscricoes]
    )


@interna.get("/inscricoes/{inscricao_id}", response_model=Resposta[InscricaoInterna])
def inscricao_detalhada(inscricao_id: int, db: Sessao):
    """Notas e frequências de uma inscrição, para o worker recalcular o risco."""
    inscricao = InscricaoRepositorio(db).obter_detalhada(inscricao_id)
    if inscricao is None:
        raise RecursoNaoEncontrado(f"Inscrição {inscricao_id} não encontrada.")
    return resposta(InscricaoInterna, inscricao)
