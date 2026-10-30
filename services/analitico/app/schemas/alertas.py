"""Schemas de alertas precoces e acompanhamento (RF07)."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

TipoAlerta = Literal["queda", "frequencia", "abandono"]
NivelAlerta = Literal["atencao", "alto"]
EstadoAtendimento = Literal["pendente", "acomp", "encerrado"]
TipoAcompanhamento = Literal["contato", "orientacao", "monitoria"]


class AlertaSaida(BaseModel):
    aluno_id: int
    aluno_nome: str
    matricula: str
    disciplina_id: int
    disciplina_nome: str
    professor_id: int | None
    tipo: TipoAlerta
    nivel: NivelAlerta
    titulo: str
    detalhe: str
    acao_sugerida: str
    estado: EstadoAtendimento
    ultimo_contato: str


class ResumoTipo(BaseModel):
    tipo: TipoAlerta
    total: int
    graves: int
    pendentes: int


class ListaAlertas(BaseModel):
    """`resumo` conta o recorte (turma, disciplina, período) antes dos filtros de tipo e nível."""

    resumo: list[ResumoTipo]
    alertas: list[AlertaSaida]


class AtendimentoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aluno_id: int
    tipo: TipoAlerta
    disciplina_id: int
    estado: EstadoAtendimento


class AcompanhamentoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    aluno_id: int
    disciplina_id: int | None = None
    tipo: TipoAcompanhamento
    data: date
    responsavel: Annotated[str, StringConstraints(min_length=2, max_length=60)] | None = None
    observacao: Annotated[str, StringConstraints(min_length=3, max_length=200)]
    revisao: date | None = None
    visivel_ao_aluno: bool = False


class AcompanhamentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    disciplina_id: int | None
    tipo: TipoAcompanhamento
    data: date
    responsavel: str
    observacao: str
    revisao: date | None
    revisao_feita: bool
    revisao_vencida: bool = False
    visivel_ao_aluno: bool
    criado_em: datetime
