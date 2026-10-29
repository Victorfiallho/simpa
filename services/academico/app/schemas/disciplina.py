from typing import Annotated, Literal

from pydantic import Field

from app.schemas.base import Codigo, Entrada, PeriodoLetivo, Saida, Texto

StatusDisciplina = Literal["ativa", "inativa", "encerrada"]
CargaHoraria = Annotated[int, Field(gt=0, le=400)]


class DisciplinaCriacao(Entrada):
    codigo: Codigo | None = None
    nome: Texto
    carga_horaria: CargaHoraria
    periodo_letivo: PeriodoLetivo
    turma_id: int
    professor_id: int | None = None


class DisciplinaAtualizacao(Entrada):
    codigo: Codigo | None = None
    nome: Texto | None = None
    carga_horaria: CargaHoraria | None = None
    periodo_letivo: PeriodoLetivo | None = None
    professor_id: int | None = None
    status: StatusDisciplina | None = None


class DisciplinaLeitura(Saida):
    id: int
    codigo: str | None
    nome: str
    carga_horaria: int
    periodo_letivo: str
    turma_id: int
    professor_id: int | None
    status: str


class DisciplinaResumo(Saida):
    id: int
    codigo: str | None
    nome: str
    periodo_letivo: str
    turma_id: int
    professor_id: int | None
    status: str
