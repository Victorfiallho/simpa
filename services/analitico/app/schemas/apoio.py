"""Schemas das solicitações de apoio (RF07)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

EstadoApoio = Literal["recebida", "atendimento", "concluida"]


class SolicitacaoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Nulo = pedido geral, sobre nenhuma disciplina específica.
    disciplina_id: int | None = None
    motivo: Annotated[str, StringConstraints(max_length=60)]
    texto: Annotated[str, StringConstraints(min_length=3, max_length=200)]


class EstadoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: EstadoApoio


class PassoHistorico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estado: EstadoApoio
    em: datetime


class SolicitacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    disciplina_id: int | None
    motivo: str
    texto: str
    estado: EstadoApoio
    criada_em: datetime
    atualizada_em: datetime
    historico: list[PassoHistorico] = []


class SolicitacaoDaCoordenacao(SolicitacaoSaida):
    """Na visão da coordenação, o pedido traz quem pediu."""

    aluno_nome: str | None = None
    matricula: str | None = None
    disciplina_nome: str | None = None
