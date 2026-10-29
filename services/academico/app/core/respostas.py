"""Formato padrão de resposta da API (RF08, RF10, RNF14), igual nos três serviços.

Toda resposta tem `status`, `mensagem`, `dados` e `erro`. Listagens trazem também
`pagina`, `limite` e `total_registros`.
"""

from collections.abc import Sequence
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)


class CampoInvalido(BaseModel):
    campo: str
    regra: str
    mensagem: str


class Erro(BaseModel):
    codigo: str
    mensagem: str
    campos: list[CampoInvalido] = []


class Resposta(BaseModel, Generic[T]):
    status: Literal["sucesso", "erro"] = "sucesso"
    mensagem: str = "OK"
    dados: T | None = None
    erro: Erro | None = None


class RespostaPaginada(Resposta[list[T]], Generic[T]):
    pagina: int
    limite: int
    total_registros: int


def resposta(schema: type[S], objeto: Any, mensagem: str = "OK") -> Resposta[S]:
    """Converte um objeto do banco para o schema de saída e embrulha no envelope."""
    return Resposta[schema](dados=schema.model_validate(objeto), mensagem=mensagem)


def resposta_paginada(
    schema: type[S], itens: Sequence[Any], total: int, pagina: int, limite: int
) -> RespostaPaginada[S]:
    return RespostaPaginada[schema](
        dados=[schema.model_validate(item) for item in itens],
        pagina=pagina,
        limite=limite,
        total_registros=total,
    )


def corpo_de_erro(codigo: str, mensagem: str, campos: list[CampoInvalido] | None = None) -> dict:
    return Resposta[None](
        status="erro",
        mensagem=mensagem,
        erro=Erro(codigo=codigo, mensagem=mensagem, campos=campos or []),
    ).model_dump()
