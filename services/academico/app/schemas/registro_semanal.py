from datetime import date
from typing import Annotated, Self

from pydantic import AfterValidator, Field, model_validator

from app.schemas.base import Entrada, Saida

Quantidade = Annotated[int, Field(ge=0, le=50)]


def _segunda_feira(valor: date) -> date:
    if valor.weekday() != 0:
        raise ValueError("A semana é identificada pela segunda-feira.")
    return valor


SemanaInicio = Annotated[date, AfterValidator(_segunda_feira)]


class RegistroSemanalCriacao(Entrada):
    inscricao_id: int
    semana_inicio: SemanaInicio
    presente: bool
    atividades_previstas: Quantidade = 0
    atividades_entregues: Quantidade = 0

    @model_validator(mode="after")
    def _entregues_ate_previstas(self) -> Self:
        if self.atividades_entregues > self.atividades_previstas:
            raise ValueError("As atividades entregues não podem passar das previstas.")
        return self


class RegistroSemanalAtualizacao(Entrada):
    presente: bool | None = None
    atividades_previstas: Quantidade | None = None
    atividades_entregues: Quantidade | None = None


class RegistroSemanalLeitura(Saida):
    id: int
    inscricao_id: int
    semana_inicio: date
    presente: bool
    atividades_previstas: int
    atividades_entregues: int
