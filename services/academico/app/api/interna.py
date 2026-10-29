"""Rotas /internal: só para outros serviços, na rede interna do Docker (D14).

O gateway bloqueia /api/*/internal, então estas rotas não ficam expostas para fora.
"""

from fastapi import APIRouter

from app.api.dependencias import Sessao
from app.core.excecoes import RecursoNaoEncontrado
from app.core.respostas import Resposta, resposta
from app.repositories.academico import InscricaoRepositorio
from app.schemas.inscricao import InscricaoDetalhada

interna = APIRouter(prefix="/internal", tags=["Interno"], include_in_schema=False)


@interna.get("/inscricoes/{inscricao_id}", response_model=Resposta[InscricaoDetalhada])
def inscricao_detalhada(inscricao_id: int, db: Sessao):
    """Notas e frequências de uma inscrição, para o analítico calcular o risco."""
    inscricao = InscricaoRepositorio(db).obter_detalhada(inscricao_id)
    if inscricao is None:
        raise RecursoNaoEncontrado(f"Inscrição {inscricao_id} não encontrada.")
    return resposta(InscricaoDetalhada, inscricao)
