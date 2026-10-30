"""Rotas de cenários: projeção de aprovação e margem por aluno (RF07).

Só admin e coordenador. Nada é gravado: as regras vêm na própria requisição.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.clientes import academico
from app.core.excecoes import AcessoNegado
from app.core.respostas import Resposta
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.schemas.cenarios import MargemSaida, Projecao
from app.services import cenarios
from app.services.cenarios import Base, Regras

PERFIS = {"admin", "coordenador"}


def gestor(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
    if usuario.role not in PERFIS:
        raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
    return usuario


Nota = Annotated[Decimal, Query(ge=0, le=10, max_digits=4, decimal_places=2)]
BaseQuery = Annotated[
    Base,
    Query(description="n1: só a N1 conta e a N2 é estimada; atual: usa N1 e N2 lançadas"),
]

cenario = APIRouter(prefix="/cenarios", tags=["Cenários"], dependencies=[Depends(gestor)])


def _regras(aprovacao: Decimal, recuperacao: Decimal, final: Decimal) -> Regras:
    regras = Regras(aprovacao, recuperacao, final)
    regras.validar()
    return regras


@cenario.get("/projecao", response_model=Resposta[Projecao])
def projecao(
    aprovacao: Nota = Decimal(6),
    recuperacao: Nota = Decimal(4),
    final: Nota = Decimal(5),
    base: BaseQuery = "n1",
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    periodo_letivo: str | None = None,
    limite_metas: Annotated[int, Query(ge=1, le=500)] = 60,
):
    """Projeta aprovação, recuperação e reprovação com as regras informadas, e lista as metas."""
    regras = _regras(aprovacao, recuperacao, final)
    inscricoes = academico.buscar_inscricoes(
        turma_id=turma_id, disciplina_id=disciplina_id, periodo_letivo=periodo_letivo
    )
    dados = cenarios.montar_projecao(inscricoes, regras, base, limite_metas)
    return Resposta[Projecao](dados=dados)


@cenario.get("/margem/{inscricao_id}", response_model=Resposta[MargemSaida])
def margem(
    inscricao_id: int,
    aprovacao: Nota = Decimal(6),
    recuperacao: Nota = Decimal(4),
    final: Nota = Decimal(5),
    base: BaseQuery = "atual",
    hipotese: Annotated[
        Decimal | None,
        Query(ge=0, le=10, max_digits=4, decimal_places=2, description="Nota hipotética"),
    ] = None,
):
    """Nota mínima que falta para aprovar (N2 ou exame) e o resultado de uma nota hipotética."""
    regras = _regras(aprovacao, recuperacao, final)
    inscricao = academico.buscar_inscricao(inscricao_id)
    dados = cenarios.margem_da_inscricao(inscricao, regras, base, hipotese)
    return Resposta[MargemSaida](dados=dados)
