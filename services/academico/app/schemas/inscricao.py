from datetime import datetime
from typing import Literal

from app.schemas.avaliacao import AvaliacaoLeitura
from app.schemas.base import Entrada, Saida
from app.schemas.disciplina import DisciplinaResumo
from app.schemas.frequencia import FrequenciaLeitura

StatusInscricao = Literal["ativa", "trancada", "concluida", "cancelada"]


class InscricaoCriacao(Entrada):
    aluno_id: int
    disciplina_id: int


class InscricaoAtualizacao(Entrada):
    status: StatusInscricao


class InscricaoLeitura(Saida):
    id: int
    aluno_id: int
    disciplina_id: int
    status: str
    criado_em: datetime


class InscricaoDetalhada(Saida):
    """Inscrição com a disciplina, as notas e a frequência (RF04 e rota /internal)."""

    id: int
    aluno_id: int
    status: str
    disciplina: DisciplinaResumo
    avaliacoes: list[AvaliacaoLeitura]
    frequencias: list[FrequenciaLeitura]
