from datetime import datetime
from typing import Literal

from app.schemas.avaliacao import AvaliacaoLeitura
from app.schemas.base import Entrada, Saida
from app.schemas.disciplina import DisciplinaResumo
from app.schemas.frequencia import FrequenciaLeitura
from app.schemas.registro_semanal import RegistroSemanalLeitura

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
    """Inscrição com a disciplina, as notas e a frequência (RF04)."""

    id: int
    aluno_id: int
    status: str
    disciplina: DisciplinaResumo
    avaliacoes: list[AvaliacaoLeitura]
    frequencias: list[FrequenciaLeitura]


class TurmaResumo(Saida):
    id: int
    codigo: str | None
    nome: str
    status: str


class AlunoResumo(Saida):
    id: int
    matricula: str
    nome_completo: str
    email: str
    turma_id: int
    status: str


class DisciplinaInterna(DisciplinaResumo):
    turma: TurmaResumo


class InscricaoInterna(Saida):
    """Tudo o que o analítico precisa de uma inscrição para calcular indicadores e risco."""

    id: int
    status: str
    aluno: AlunoResumo
    disciplina: DisciplinaInterna
    avaliacoes: list[AvaliacaoLeitura]
    frequencias: list[FrequenciaLeitura]
    semanas: list[RegistroSemanalLeitura] = []
