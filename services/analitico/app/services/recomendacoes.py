"""Recomendações de acompanhamento a partir dos critérios de risco (Nível 2, D21).

São heurísticas: regras simples e explicáveis, ligadas a cada critério violado. Sugerem
uma ação; quem decide é a coordenação.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from app.services.regras import FREQUENCIA_ATENCAO, MEDIA_ATENCAO, formatar

if TYPE_CHECKING:
    from app.services.painel import InscricaoCalculada

Prioridade = Literal["alta", "media", "baixa"]
ORDEM = {"alta": 0, "media": 1, "baixa": 2}


@dataclass(frozen=True)
class Recomendacao:
    prioridade: Prioridade
    disciplina: str | None
    acao: str
    motivo: str


def _da_inscricao(c: InscricaoCalculada, media_projetada: Decimal | None) -> list[Recomendacao]:
    nome = c.inscricao.disciplina.nome
    classe = c.classificacao
    criterios = set(classe.criterios)

    if criterios == {"media_baixa", "frequencia_baixa"}:
        return [
            Recomendacao(
                "alta",
                nome,
                f"Reunião com o aluno e plano de recuperação em {nome}",
                f"média {formatar(classe.media)} e frequência {formatar(classe.frequencia)}% "
                "abaixo do mínimo",
            )
        ]
    if "media_baixa" in criterios:
        return [
            Recomendacao(
                "alta",
                nome,
                f"Encaminhar para monitoria ou aulas de reforço em {nome}",
                f"média {formatar(classe.media)}, abaixo de 6,00",
            )
        ]
    if "frequencia_baixa" in criterios:
        return [
            Recomendacao(
                "alta",
                nome,
                f"Contato da coordenação sobre as faltas em {nome}, para entender o motivo",
                f"frequência {formatar(classe.frequencia)}%, abaixo de 75%",
            )
        ]
    if classe.status == "indeterminado":
        return [
            Recomendacao(
                "baixa",
                nome,
                f"Pedir ao professor o lançamento das notas e da frequência de {nome}",
                "sem dados suficientes para avaliar",
            )
        ]

    sugestoes = []
    if media_projetada is not None and media_projetada < Decimal("6.00"):
        sugestoes.append(
            Recomendacao(
                "media",
                nome,
                f"Acompanhar de perto a próxima avaliação de {nome}",
                f"a projeção da regressão indica média final {formatar(media_projetada)}",
            )
        )
    if classe.media is not None and classe.media < MEDIA_ATENCAO:
        sugestoes.append(
            Recomendacao(
                "media",
                nome,
                f"Sugerir monitoria preventiva em {nome}",
                f"média {formatar(classe.media)}, perto do mínimo",
            )
        )
    if classe.frequencia is not None and classe.frequencia < FREQUENCIA_ATENCAO:
        sugestoes.append(
            Recomendacao(
                "media",
                nome,
                f"Lembrar o aluno do limite de 75% de presença em {nome}",
                f"frequência {formatar(classe.frequencia)}%, perto do mínimo",
            )
        )
    return sugestoes


def recomendar(
    calculadas: Iterable[InscricaoCalculada], projecoes: dict[int, Decimal]
) -> list[Recomendacao]:
    """Recomendações de um aluno, da mais para a menos urgente."""
    lista = list(calculadas)
    recomendacoes = [r for c in lista for r in _da_inscricao(c, projecoes.get(c.inscricao.id))]
    em_risco = sum(c.classificacao.status == "em_risco" for c in lista)
    if em_risco >= 2:
        recomendacoes.insert(
            0,
            Recomendacao(
                "alta",
                None,
                "Conversa com a coordenação sobre a carga do semestre",
                f"em risco em {em_risco} disciplinas ao mesmo tempo",
            ),
        )
    return sorted(recomendacoes, key=lambda r: ORDEM[r.prioridade])
