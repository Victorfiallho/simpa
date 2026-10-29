"""Bases e validadores comuns dos schemas (RF10)."""

import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints


class Entrada(BaseModel):
    """Schema de entrada: rejeita campos desconhecidos e tira espaços das pontas."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Saida(BaseModel):
    """Schema de saída: lido direto dos objetos do banco."""

    model_config = ConfigDict(from_attributes=True)


Texto = Annotated[str, StringConstraints(min_length=1, max_length=120)]
PeriodoLetivo = Annotated[str, StringConstraints(pattern=r"^\d{4}\.[12]$")]
PeriodoAvaliacao = Annotated[str, StringConstraints(pattern=r"^N[1-4]$")]
Codigo = Annotated[str, StringConstraints(min_length=1, max_length=20)]


def cpf_valido(valor: str) -> str:
    """Aceita com ou sem pontuação, devolve só os 11 dígitos e confere os verificadores."""
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValueError("CPF inválido.")
    for tamanho in (9, 10):
        pesos = range(tamanho + 1, 1, -1)
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], pesos, strict=True))
        verificador = (soma * 10) % 11 % 10
        if verificador != int(digitos[tamanho]):
            raise ValueError("CPF inválido: dígito verificador não confere.")
    return digitos


CPF = Annotated[str, AfterValidator(cpf_valido)]


def mascarar_cpf(cpf: str | None) -> str | None:
    """Só os 6 dígitos do meio aparecem nas respostas (RNF04): ***.456.789-**"""
    return None if cpf is None else f"***.{cpf[3:6]}.{cpf[6:9]}-**"


def duas_casas(valor: Decimal) -> Decimal:
    """Arredondamento HALF_UP em 2 casas (D06)."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
