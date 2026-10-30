"""Rota do copiloto: perguntas em linguagem natural sobre a turma (RF07). Só admin e coordenador."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.clientes import academico
from app.core.excecoes import AcessoNegado
from app.core.respostas import Resposta
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.schemas.copiloto import Pergunta, RespostaCopiloto
from app.services import copiloto


def gestor(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
    if usuario.role not in {"admin", "coordenador"}:
        raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
    return usuario


router = APIRouter(prefix="/copiloto", tags=["Copiloto"], dependencies=[Depends(gestor)])


@router.post("/perguntas", response_model=Resposta[RespostaCopiloto])
def perguntar(dados: Pergunta):
    """Responde por regras, sem modelo de linguagem: cada resposta cita o recorte usado."""
    inscricoes = academico.buscar_inscricoes()
    return Resposta[RespostaCopiloto](dados=copiloto.responder(dados.pergunta, inscricoes))


@router.get("/sugestoes", response_model=Resposta[list[str]])
def sugestoes():
    return Resposta[list[str]](dados=copiloto.SUGESTOES)
