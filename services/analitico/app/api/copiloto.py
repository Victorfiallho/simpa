"""Rota do copiloto: perguntas em linguagem natural sobre a turma (RF07). Só admin e coordenador."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.database import get_db
from app.core.respostas import Resposta
from app.core.seguranca import exigir_roles
from app.schemas.copiloto import Pergunta, RespostaCopiloto
from app.services import copiloto

router = APIRouter(
    prefix="/copiloto",
    tags=["Copiloto"],
    dependencies=[Depends(exigir_roles("admin", "coordenador"))],
)


@router.post("/perguntas", response_model=Resposta[RespostaCopiloto])
def perguntar(dados: Pergunta, db: Annotated[Session, Depends(get_db)]):
    """Responde por regras, sem modelo de linguagem: cada resposta cita o recorte usado."""
    inscricoes = academico.buscar_inscricoes()
    return Resposta[RespostaCopiloto](dados=copiloto.responder(dados.pergunta, inscricoes, db))


@router.get("/sugestoes", response_model=Resposta[list[str]])
def sugestoes():
    return Resposta[list[str]](dados=copiloto.SUGESTOES)
