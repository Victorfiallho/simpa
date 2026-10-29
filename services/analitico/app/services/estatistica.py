"""Estatística descritiva (RF05, D06, D07). Funções puras, em Decimal.

Variância populacional (÷ n) quando o conjunto é o universo completo do recorte;
amostral (÷ n − 1) quando é um subconjunto, como a janela parcial N1. Na amostral com
n < 2 não há variância: o resultado vem nulo com a observação "amostra insuficiente".
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.services.regras import arredondar

TipoVariancia = Literal["populacional", "amostral"]


@dataclass(frozen=True)
class Resumo:
    n: int
    media: Decimal | None
    mediana: Decimal | None
    variancia: Decimal | None
    desvio_padrao: Decimal | None
    minimo: Decimal | None
    maximo: Decimal | None
    tipo_variancia: TipoVariancia
    observacao: str | None = None


def _ou_nulo(valor: Decimal | None) -> Decimal | None:
    return None if valor is None else arredondar(valor)


def resumir(valores: Sequence[Decimal], *, amostral: bool) -> Resumo:
    tipo: TipoVariancia = "amostral" if amostral else "populacional"
    n = len(valores)
    if n == 0:
        return Resumo(0, None, None, None, None, None, None, tipo, "sem dados")

    ordenados = sorted(valores)
    media = sum(ordenados, Decimal(0)) / n
    meio = n // 2
    mediana = ordenados[meio] if n % 2 else (ordenados[meio - 1] + ordenados[meio]) / 2

    divisor = n - 1 if amostral else n
    variancia = None
    observacao = None
    if divisor == 0:
        observacao = "amostra insuficiente"
    else:
        variancia = sum(((v - media) ** 2 for v in ordenados), Decimal(0)) / divisor

    return Resumo(
        n=n,
        media=arredondar(media),
        mediana=arredondar(mediana),
        variancia=_ou_nulo(variancia),
        desvio_padrao=_ou_nulo(variancia.sqrt() if variancia is not None else None),
        minimo=ordenados[0],
        maximo=ordenados[-1],
        tipo_variancia=tipo,
        observacao=observacao,
    )


def histograma(valores: Sequence[Decimal], faixas: int = 10) -> list[int]:
    """Quantidade de valores de 0 a 10 em faixas de 1 ponto; a última inclui o 10."""
    contagem = [0] * faixas
    for valor in valores:
        contagem[min(faixas - 1, int(valor))] += 1
    return contagem


def correlacao(xs: Sequence[Decimal], ys: Sequence[Decimal]) -> Decimal | None:
    """Correlação de Pearson. Descreve associação linear, não causa nem previsão."""
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    media_x = sum(xs, Decimal(0)) / n
    media_y = sum(ys, Decimal(0)) / n
    cruzado = sum(((x - media_x) * (y - media_y) for x, y in zip(xs, ys, strict=True)), Decimal(0))
    soma_x = sum(((x - media_x) ** 2 for x in xs), Decimal(0))
    soma_y = sum(((y - media_y) ** 2 for y in ys), Decimal(0))
    if soma_x == 0 or soma_y == 0:
        return None
    return arredondar(cruzado / (soma_x * soma_y).sqrt())
