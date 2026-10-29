from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, computed_field, model_validator

from app.schemas.base import Entrada, PeriodoAvaliacao, Saida, duas_casas

AulasPrevistas = Annotated[int, Field(gt=0, le=500)]
Faltas = Annotated[int, Field(ge=0, le=500)]


class FrequenciaCriacao(Entrada):
    """O percentual não é aceito na entrada: é sempre derivado (D02)."""

    inscricao_id: int
    periodo_avaliacao: PeriodoAvaliacao
    aulas_previstas: AulasPrevistas
    faltas: Faltas

    @model_validator(mode="after")
    def _faltas_ate_aulas(self) -> Self:
        if self.faltas > self.aulas_previstas:
            raise ValueError("As faltas não podem passar das aulas previstas.")
        return self


class FrequenciaAtualizacao(Entrada):
    periodo_avaliacao: PeriodoAvaliacao | None = None
    aulas_previstas: AulasPrevistas | None = None
    faltas: Faltas | None = None


class FrequenciaLeitura(Saida):
    id: int
    inscricao_id: int
    periodo_avaliacao: str
    aulas_previstas: int
    faltas: int

    @computed_field
    @property
    def frequencia_percentual(self) -> Decimal:
        presencas = Decimal(self.aulas_previstas - self.faltas)
        return duas_casas(presencas * 100 / Decimal(self.aulas_previstas))
