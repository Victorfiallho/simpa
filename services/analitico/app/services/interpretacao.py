"""Interpretação automática: transforma os indicadores em achados escritos (D21).

Cada achado é um padrão que o sistema detecta nos dados (onde está o risco, de onde ele
vem, o que melhorou ou piorou, como as variáveis se relacionam) e descreve em uma frase.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from app.services import estatistica
from app.services.regras import arredondar, formatar

if TYPE_CHECKING:
    from app.services.painel import InscricaoCalculada

Gravidade = Literal["alerta", "atencao", "info"]
ORDEM = {"alerta": 0, "atencao": 1, "info": 2}
VARIACAO_RELEVANTE = Decimal("0.20")
MINIMO_POR_GRUPO = 3


@dataclass(frozen=True)
class Achado:
    gravidade: Gravidade
    titulo: str
    texto: str


def _pct(parte: int, total: int) -> str:
    return f"{round(100 * parte / total)}%" if total else "0%"


def _media(valores: list[Decimal]) -> Decimal | None:
    return arredondar(sum(valores, Decimal(0)) / len(valores)) if valores else None


def _rotulo(c: InscricaoCalculada) -> str:
    turma = c.inscricao.disciplina.turma
    sufixo = turma.codigo.split("-")[-1] if turma.codigo else turma.nome
    return f"{c.inscricao.disciplina.nome} (turma {sufixo})"


def gerar_achados(
    calculadas: list[InscricaoCalculada], situacoes_alunos: dict[str, int]
) -> list[Achado]:
    validas = [c for c in calculadas if c.classificacao.status != "indeterminado"]
    if not validas:
        return [
            Achado(
                "info",
                "Sem dados suficientes",
                "Ainda não há notas e frequências lançadas neste recorte.",
            )
        ]

    achados: list[Achado] = []
    total_alunos = sum(situacoes_alunos.values())
    em_risco_alunos = situacoes_alunos.get("em_risco", 0)
    atencao_alunos = situacoes_alunos.get("atencao", 0)

    # 1. Tamanho do problema
    proporcao = em_risco_alunos / total_alunos if total_alunos else 0
    achados.append(
        Achado(
            "alerta" if proporcao >= 0.2 else "atencao" if em_risco_alunos else "info",
            "Alunos em risco",
            f"{em_risco_alunos} de {total_alunos} alunos ({_pct(em_risco_alunos, total_alunos)}) "
            "estão em risco em pelo menos uma disciplina."
            + (
                f" Outros {atencao_alunos} estão perto do limite (atenção)."
                if atencao_alunos
                else ""
            ),
        )
    )

    # 2. De onde vem o risco: nota, falta ou as duas
    em_risco = [c for c in validas if c.classificacao.status == "em_risco"]
    if em_risco:
        por_media = sum("media_baixa" in c.classificacao.criterios for c in em_risco)
        por_frequencia = sum("frequencia_baixa" in c.classificacao.criterios for c in em_risco)
        principal = "das notas" if por_media >= por_frequencia else "das faltas"
        achados.append(
            Achado(
                "atencao",
                "Origem do risco",
                f"O risco vem principalmente {principal}: das {len(em_risco)} inscrições em risco, "
                f"{por_media} com média abaixo de 6,00 e {por_frequencia} com frequência abaixo "
                "de 75% (uma inscrição pode ter os dois).",
            )
        )

    # 3. Onde o risco se concentra
    por_oferta: dict[str, list[InscricaoCalculada]] = {}
    for c in validas:
        por_oferta.setdefault(_rotulo(c), []).append(c)
    grupos = {k: v for k, v in por_oferta.items() if len(v) >= MINIMO_POR_GRUPO}
    if em_risco and len(grupos) > 1:
        rotulo, lista = max(
            grupos.items(),
            key=lambda item: (
                sum(c.classificacao.status == "em_risco" for c in item[1]) / len(item[1])
            ),
        )
        riscos = sum(c.classificacao.status == "em_risco" for c in lista)
        media = _media([c.media for c in lista if c.media is not None])
        if riscos:
            achados.append(
                Achado(
                    "alerta" if riscos / len(lista) >= 0.25 else "atencao",
                    "Disciplina mais crítica",
                    f"{rotulo} tem a maior proporção de inscrições em risco: {riscos} de "
                    f"{len(lista)} ({_pct(riscos, len(lista))}), com média {formatar(media)}.",
                )
            )

    # 4. Tendência da N1 para o acumulado
    variacoes = []
    for rotulo, lista in grupos.items():
        pares = [
            (c.media_n1, c.media) for c in lista if c.media_n1 is not None and c.media is not None
        ]
        if len(pares) >= MINIMO_POR_GRUPO:
            antes = _media([p[0] for p in pares])
            depois = _media([p[1] for p in pares])
            variacoes.append((depois - antes, rotulo, antes, depois))
    if variacoes:
        queda = min(variacoes)
        alta = max(variacoes)
        if queda[0] <= -VARIACAO_RELEVANTE:
            achados.append(
                Achado(
                    "atencao",
                    "Queda de desempenho",
                    f"Em {queda[1]} a média caiu {formatar(-queda[0])} ponto da N1 "
                    f"({formatar(queda[2])}) para o acumulado ({formatar(queda[3])}).",
                )
            )
        if alta[0] >= VARIACAO_RELEVANTE:
            achados.append(
                Achado(
                    "info",
                    "Melhora de desempenho",
                    f"Em {alta[1]} a média subiu {formatar(alta[0])} ponto da N1 "
                    f"({formatar(alta[2])}) para o acumulado ({formatar(alta[3])}).",
                )
            )
        if queda[0] > -VARIACAO_RELEVANTE and alta[0] < VARIACAO_RELEVANTE:
            achados.append(
                Achado(
                    "info",
                    "Desempenho estável",
                    "Nenhuma disciplina variou mais de 0,20 ponto entre a N1 e o acumulado.",
                )
            )

    # 5. Relação entre frequência e nota
    r = estatistica.correlacao(
        [c.frequencia for c in validas if c.frequencia is not None],
        [c.media for c in validas if c.media is not None],
    )
    if r is not None:
        forca = abs(r)
        intensidade = (
            "forte"
            if forca >= Decimal("0.5")
            else "moderada"
            if forca >= Decimal("0.3")
            else "fraca"
            if forca >= Decimal("0.1")
            else "praticamente inexistente"
        )
        sentido = (
            "quem frequenta mais tende a ter notas maiores"
            if r > 0
            else ("quem frequenta mais tende a ter notas menores")
        )
        achados.append(
            Achado(
                "info",
                "Frequência e nota",
                f"A correlação entre frequência e média é {intensidade} (r = {formatar(r)})"
                + (f": {sentido}." if forca >= Decimal("0.1") else ".")
                + " É associação, não causa.",
            )
        )

    # 6. Homogeneidade da turma
    resumo = estatistica.resumir([c.media for c in validas if c.media is not None], amostral=False)
    if resumo.media and resumo.desvio_padrao is not None:
        cv = resumo.desvio_padrao / resumo.media
        achados.append(
            Achado(
                "info",
                "Dispersão das notas",
                f"Desvio padrão de {formatar(resumo.desvio_padrao)} ponto em torno da média "
                f"{formatar(resumo.media)}: desempenho "
                + (
                    "heterogêneo, com alunos muito distantes da média."
                    if cv > Decimal("0.2")
                    else "relativamente homogêneo."
                ),
            )
        )

    return sorted(achados, key=lambda a: ORDEM[a.gravidade])
