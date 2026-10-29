"""Regras de média, frequência e risco acadêmico (RF07, D04, D05, D06, D08, D09).

Funções puras: recebem números e devolvem resultados, sem banco e sem rede. Tudo em
Decimal, arredondado para 2 casas (ROUND_HALF_UP) ANTES de classificar (D06): o valor
exibido é sempre o valor usado na decisão.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENTESIMO = Decimal("0.01")
MEDIA_MINIMA = Decimal("6.00")
FREQUENCIA_MINIMA = Decimal("75.00")
MEDIA_ATENCAO = Decimal("7.00")
FREQUENCIA_ATENCAO = Decimal("80.00")


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTESIMO, rounding=ROUND_HALF_UP)


def formatar(valor: Decimal) -> str:
    """Decimal → texto em português com 2 casas: Decimal("4.5") → "4,50"."""
    return f"{arredondar(valor):.2f}".replace(".", ",")


def media_ponderada(notas: Iterable[tuple[Decimal, Decimal]]) -> Decimal | None:
    """Média das notas pelo peso (D05). None quando não há nota lançada."""
    pares = list(notas)
    soma_pesos = sum((peso for _, peso in pares), Decimal(0))
    if soma_pesos == 0:
        return None
    return arredondar(sum((nota * peso for nota, peso in pares), Decimal(0)) / soma_pesos)


def percentual_de_frequencia(aulas: int, faltas: int) -> Decimal | None:
    """(aulas − faltas) / aulas × 100 (D05). None quando não há aula registrada."""
    if aulas <= 0:
        return None
    return arredondar(Decimal(aulas - faltas) * 100 / Decimal(aulas))


@dataclass(frozen=True)
class Classificacao:
    status: str  # em_risco | sem_risco | indeterminado
    atencao: bool
    criterios: tuple[str, ...]
    justificativa: str
    media: Decimal | None
    frequencia: Decimal | None

    @property
    def situacao(self) -> str:
        """As 4 situações visuais: "atencao" é um sinal sobre Sem risco, não uma classe (D08)."""
        return "atencao" if self.status == "sem_risco" and self.atencao else self.status


def classificar(
    disciplina: str, media: Decimal | None, frequencia: Decimal | None
) -> Classificacao:
    """Classifica uma inscrição e explica o porquê, citando disciplina, média e frequência."""
    if media is None or frequencia is None:
        faltando = " e ".join(
            nome for nome, valor in (("notas", media), ("frequência", frequencia)) if valor is None
        )
        return Classificacao(
            "indeterminado",
            False,
            (),
            f"{disciplina}: sem {faltando} lançadas — dados_insuficientes",
            media,
            frequencia,
        )

    criterios: list[str] = []
    motivos: list[str] = []
    if media < MEDIA_MINIMA:
        criterios.append("media_baixa")
        motivos.append(f"média {formatar(media)} (< 6,00) — media_baixa")
    if frequencia < FREQUENCIA_MINIMA:
        criterios.append("frequencia_baixa")
        motivos.append(f"frequência {formatar(frequencia)}% (< 75,00%) — frequencia_baixa")
    if criterios:
        return Classificacao(
            "em_risco",
            False,
            tuple(criterios),
            f"{disciplina}: {'; '.join(motivos)}",
            media,
            frequencia,
        )

    alertas: list[str] = []
    if media < MEDIA_ATENCAO:
        alertas.append(f"média {formatar(media)} abaixo de 7,00")
    if frequencia < FREQUENCIA_ATENCAO:
        alertas.append(f"frequência {formatar(frequencia)}% abaixo de 80,00%")
    if alertas:
        justificativa = f"{disciplina}: sem risco, em atenção — {' e '.join(alertas)}"
    else:
        justificativa = (
            f"{disciplina}: média {formatar(media)} e frequência {formatar(frequencia)}%"
            " — sem risco"
        )
    return Classificacao("sem_risco", bool(alertas), (), justificativa, media, frequencia)


def consolidar(classificacoes: Iterable[Classificacao]) -> tuple[str, bool]:
    """Status do aluno a partir das inscrições ativas (D04, D19).

    Qualquer inscrição em risco torna o aluno Em risco. Inscrições sem dados não contam
    (D09): o aluno só fica Indeterminado se nenhuma inscrição tiver dados suficientes.
    """
    lista = list(classificacoes)
    if any(c.status == "em_risco" for c in lista):
        return "em_risco", False
    validas = [c for c in lista if c.status == "sem_risco"]
    if not validas:
        return "indeterminado", False
    return "sem_risco", any(c.atencao for c in validas)


def situacao(status: str, atencao: bool) -> str:
    return "atencao" if status == "sem_risco" and atencao else status
