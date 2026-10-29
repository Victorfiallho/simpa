from typing import Literal

from app.schemas.base import Codigo, Entrada, PeriodoLetivo, Saida, Texto

StatusTurma = Literal["ativa", "inativa", "encerrada"]
Turno = Literal["matutino", "vespertino", "noturno", "integral"]


class TurmaCriacao(Entrada):
    codigo: Codigo | None = None
    nome: Texto
    curso: Texto
    periodo_letivo: PeriodoLetivo
    turno: Turno
    sala: Codigo | None = None


class TurmaAtualizacao(Entrada):
    codigo: Codigo | None = None
    nome: Texto | None = None
    curso: Texto | None = None
    periodo_letivo: PeriodoLetivo | None = None
    turno: Turno | None = None
    sala: Codigo | None = None
    status: StatusTurma | None = None


class TurmaLeitura(Saida):
    id: int
    codigo: str | None
    nome: str
    curso: str
    periodo_letivo: str
    turno: str
    sala: str | None
    status: str
