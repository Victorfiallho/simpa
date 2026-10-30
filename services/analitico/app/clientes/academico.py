"""Cliente da API interna do serviço acadêmico (D14).

O analítico não tem cópia das notas: busca sempre os valores atuais no acadêmico.
"""

from datetime import date
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.excecoes import RecursoNaoEncontrado, ServicoIndisponivel


class Turma(BaseModel):
    id: int
    codigo: str | None
    nome: str
    status: str


class Disciplina(BaseModel):
    id: int
    codigo: str | None
    nome: str
    periodo_letivo: str
    turma_id: int
    professor_id: int | None
    status: str
    turma: Turma


class Aluno(BaseModel):
    id: int
    matricula: str
    nome_completo: str
    email: str
    turma_id: int
    status: str


class Avaliacao(BaseModel):
    periodo_avaliacao: str
    nota: Decimal
    peso: Decimal


class Frequencia(BaseModel):
    periodo_avaliacao: str
    aulas_previstas: int
    faltas: int


class Semana(BaseModel):
    """Presença e atividades de uma semana (a segunda-feira identifica a semana)."""

    semana_inicio: date
    presente: bool
    atividades_previstas: int
    atividades_entregues: int


class Inscricao(BaseModel):
    id: int
    status: str
    aluno: Aluno
    disciplina: Disciplina
    avaliacoes: list[Avaliacao]
    frequencias: list[Frequencia]
    semanas: list[Semana] = []


def _buscar(caminho: str, params: dict | None = None) -> httpx.Response:
    try:
        resposta = httpx.get(f"{get_settings().academico_url}{caminho}", params=params, timeout=15)
    except httpx.HTTPError as erro:
        raise ServicoIndisponivel("O serviço acadêmico não respondeu. Tente novamente.") from erro
    if resposta.status_code == 404:
        raise RecursoNaoEncontrado(resposta.json()["mensagem"])
    if resposta.is_error:
        raise ServicoIndisponivel("O serviço acadêmico respondeu com erro.")
    return resposta


def buscar_inscricao(inscricao_id: int) -> Inscricao:
    return Inscricao.model_validate(_buscar(f"/internal/inscricoes/{inscricao_id}").json()["dados"])


def buscar_inscricoes(
    *,
    turma_id: int | None = None,
    disciplina_id: int | None = None,
    aluno_id: int | None = None,
    periodo_letivo: str | None = None,
) -> list[Inscricao]:
    filtros = {
        "turma_id": turma_id,
        "disciplina_id": disciplina_id,
        "aluno_id": aluno_id,
        "periodo_letivo": periodo_letivo,
    }
    params = {chave: valor for chave, valor in filtros.items() if valor is not None}
    dados = _buscar("/internal/inscricoes", params).json()["dados"]
    return [Inscricao.model_validate(item) for item in dados]
