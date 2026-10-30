"""Predição da nota da N2 por regressão linear múltipla (Nível 2, D21).

Modelo: N2 = b0 + b1·N1 + b2·frequência_N1, ajustado por mínimos quadrados com as
equações normais em forma matricial:

    β = (XᵀX)⁻¹ Xᵀy

O erro é estimado por validação cruzada "deixa um de fora" (leave-one-out), calculada
de uma vez pela matriz de projeção H = X(XᵀX)⁻¹Xᵀ: o resíduo sem a observação i é
eᵢ / (1 − hᵢᵢ). Assim o erro informado não é otimista.

Os cálculos são em float (numpy): é uma estimativa, não uma classificação oficial. A
classificação de risco continua em Decimal (D06).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import TYPE_CHECKING

import numpy as np

from app.services.regras import FREQUENCIA_MINIMA, MEDIA_MINIMA, arredondar

if TYPE_CHECKING:
    from app.services.painel import InscricaoCalculada

MINIMO_DE_OBSERVACOES = 8
VARIAVEIS = ("intercepto", "nota_n1", "frequencia_n1")


@dataclass(frozen=True)
class Modelo:
    coeficientes: tuple[float, float, float]
    n: int
    r2: float
    erro_medio: float  # raiz do erro quadrático médio no próprio ajuste
    erro_validacao: float  # o mesmo, mas deixando cada observação de fora
    acerto_risco: float  # % de inscrições cujo risco final a previsão acertou (validação)
    peso_n2_padrao: Decimal

    def prever_n2(self, nota_n1: Decimal, frequencia_n1: Decimal) -> Decimal:
        b0, b1, b2 = self.coeficientes
        valor = b0 + b1 * float(nota_n1) + b2 * float(frequencia_n1)
        return arredondar(Decimal(str(min(10.0, max(0.0, valor)))))


@dataclass(frozen=True)
class Previsao:
    calculada: InscricaoCalculada
    nota_n2_prevista: Decimal
    media_projetada: Decimal
    risco_projetado: bool


def _pesos(calculada: InscricaoCalculada, periodo: str) -> Decimal:
    return sum(
        (a.peso for a in calculada.inscricao.avaliacoes if a.periodo_avaliacao == periodo),
        Decimal(0),
    )


def _treino(calculadas: list[InscricaoCalculada]) -> list[InscricaoCalculada]:
    return [
        c
        for c in calculadas
        if c.nota_n1 is not None and c.nota_n2 is not None and c.frequencia_n1 is not None
    ]


def ajustar(calculadas: list[InscricaoCalculada]) -> Modelo | None:
    """Ajusta o modelo. None quando há menos de 8 inscrições com N1, N2 e frequência."""
    treino = _treino(calculadas)
    n = len(treino)
    if n < MINIMO_DE_OBSERVACOES:
        return None

    X = np.array([[1.0, float(c.nota_n1), float(c.frequencia_n1)] for c in treino])  # noqa: N806
    y = np.array([float(c.nota_n2) for c in treino])

    XtX = X.T @ X  # noqa: N806
    try:
        beta = np.linalg.solve(XtX, X.T @ y)
        H = X @ np.linalg.inv(XtX) @ X.T  # noqa: N806
    except np.linalg.LinAlgError:
        # Variáveis colineares (ex.: todos com a mesma frequência): não há solução única.
        return None

    residuos = y - X @ beta
    soma_total = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - float((residuos**2).sum()) / soma_total if soma_total else 0.0
    alavancas = np.clip(np.diag(H), None, 0.999)
    residuos_validacao = residuos / (1 - alavancas)
    previsto_validacao = y - residuos_validacao

    peso_n2 = Decimal(str(median(float(_pesos(c, "N2")) for c in treino)))
    acertos = 0
    for c, n2_previsto in zip(treino, previsto_validacao, strict=True):
        projetada = _media_projetada(c, Decimal(str(float(n2_previsto))), peso_n2)
        risco_previsto = projetada < MEDIA_MINIMA
        risco_real = c.media is not None and c.media < MEDIA_MINIMA
        acertos += risco_previsto == risco_real

    return Modelo(
        coeficientes=(float(beta[0]), float(beta[1]), float(beta[2])),
        n=n,
        r2=r2,
        erro_medio=float(np.sqrt((residuos**2).mean())),
        erro_validacao=float(np.sqrt((residuos_validacao**2).mean())),
        acerto_risco=100 * acertos / n,
        peso_n2_padrao=peso_n2,
    )


def _media_projetada(
    calculada: InscricaoCalculada, nota_n2: Decimal, peso_n2_padrao: Decimal
) -> Decimal:
    peso_n1 = _pesos(calculada, "N1")
    peso_n2 = _pesos(calculada, "N2") or peso_n2_padrao
    return arredondar((calculada.nota_n1 * peso_n1 + nota_n2 * peso_n2) / (peso_n1 + peso_n2))


def prever(modelo: Modelo, calculadas: list[InscricaoCalculada]) -> list[Previsao]:
    """Projeta a N2 e a média final de toda inscrição que já tem N1 e frequência da N1."""
    previsoes = []
    for c in calculadas:
        if c.nota_n1 is None or c.frequencia_n1 is None:
            continue
        n2 = modelo.prever_n2(c.nota_n1, c.frequencia_n1)
        media = _media_projetada(c, n2, modelo.peso_n2_padrao)
        risco = media < MEDIA_MINIMA or c.frequencia_n1 < FREQUENCIA_MINIMA
        previsoes.append(Previsao(c, n2, media, risco))
    return previsoes


def _num(valor: float, formato: str) -> str:
    """Número com vírgula decimal: _num(0.8, "+.2f") → "+0,80"."""
    return format(valor, formato).replace(".", ",")


def descrever(modelo: Modelo) -> str:
    b0, b1, b2 = modelo.coeficientes
    return (
        f"N2 = {_num(b0, '.2f')} {'+' if b1 >= 0 else '−'} {_num(abs(b1), '.2f')}·N1 "
        f"{'+' if b2 >= 0 else '−'} {_num(abs(b2), '.3f')}·frequência N1"
    )


def interpretar(modelo: Modelo) -> list[str]:
    _, b1, b2 = modelo.coeficientes
    return [
        f"Cada ponto a mais na N1 está associado a {_num(b1, '+.2f')} ponto na N2.",
        "Cada 10 pontos percentuais a mais de frequência na N1 estão associados a "
        f"{_num(10 * b2, '+.2f')} ponto na N2.",
        f"O modelo explica {_num(100 * modelo.r2, '.0f')}% da variação da N2 (R²). Deixando "
        f"cada inscrição de fora, erra em média {_num(modelo.erro_validacao, '.2f')} ponto e "
        f"acerta o risco final em {_num(modelo.acerto_risco, '.0f')}% dos casos.",
    ]


LIMITES = [
    "É uma associação estatística, não uma relação de causa.",
    "Ajustado com poucas inscrições e com dados sintéticos: serve para demonstrar o método.",
    "Inscrições do mesmo aluno não são independentes, o que deixa o erro real um pouco maior.",
    "A projeção apoia o acompanhamento; a situação oficial continua sendo a do RF07.",
]
