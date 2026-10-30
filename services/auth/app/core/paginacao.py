"""Parâmetros de paginação e ordenação comuns a todas as listagens (RF08)."""

from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel


class Paginacao(BaseModel):
    pagina: int
    limite: int
    ordenar_por: str
    ordem: Literal["asc", "desc"]

    @property
    def deslocamento(self) -> int:
        return (self.pagina - 1) * self.limite


def paginacao(
    pagina: Annotated[int, Query(ge=1, description="Página, começando em 1")] = 1,
    limite: Annotated[int, Query(ge=1, le=100, description="Itens por página")] = 20,
    ordenar_por: Annotated[str, Query(description="Campo de ordenação")] = "id",
    ordem: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> Paginacao:
    return Paginacao(pagina=pagina, limite=limite, ordenar_por=ordenar_por, ordem=ordem)
