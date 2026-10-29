from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from app.schemas.base import Entrada, PeriodoAvaliacao, Saida

TipoAvaliacao = Literal["prova", "trabalho", "atividade", "projeto", "seminario"]
Nota = Annotated[Decimal, Field(ge=0, le=10, decimal_places=2)]
Peso = Annotated[Decimal, Field(gt=0, le=10, decimal_places=2)]


class AvaliacaoCriacao(Entrada):
    inscricao_id: int
    tipo_avaliacao: TipoAvaliacao
    periodo_avaliacao: PeriodoAvaliacao
    nota: Nota
    peso: Peso


class AvaliacaoAtualizacao(Entrada):
    tipo_avaliacao: TipoAvaliacao | None = None
    periodo_avaliacao: PeriodoAvaliacao | None = None
    nota: Nota | None = None
    peso: Peso | None = None


class AvaliacaoLeitura(Saida):
    id: int
    inscricao_id: int
    tipo_avaliacao: str
    periodo_avaliacao: str
    nota: Decimal
    peso: Decimal
    atualizado_em: datetime
