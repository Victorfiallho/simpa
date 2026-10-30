"""Monta painel e indicadores a partir das inscrições do acadêmico (RF04–RF07).

Os valores são sempre calculados na hora, a partir das notas atuais (princípio de dados
derivados). Só inscrições ativas ou concluídas entram; trancadas e canceladas ficam de fora.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.clientes.academico import Inscricao
from app.schemas.analitico import (
    AchadoSaida,
    AlunoPainel,
    FaixaHistograma,
    IndicadorDisciplina,
    Indicadores,
    InscricaoPainel,
    ModeloRegressao,
    Painel,
    PontoDispersao,
    Predicao,
    PrevisaoInscricao,
    RecomendacaoSaida,
    ResumoEstatistico,
    SituacaoOferta,
)
from app.services import estatistica, predicao
from app.services.interpretacao import gerar_achados
from app.services.recomendacoes import recomendar
from app.services.regras import (
    Classificacao,
    arredondar,
    classificar,
    consolidar,
    media_ponderada,
    percentual_de_frequencia,
    situacao,
)

Janela = Literal["acumulado", "N1"]
STATUS_QUE_CONTAM = ("ativa", "concluida")
SITUACOES = ("em_risco", "atencao", "sem_risco", "indeterminado")


@dataclass(frozen=True)
class InscricaoCalculada:
    inscricao: Inscricao
    nota_n1: Decimal | None
    nota_n2: Decimal | None
    media: Decimal | None
    media_n1: Decimal | None
    frequencia: Decimal | None
    frequencia_n1: Decimal | None
    aulas: int
    faltas: int
    classificacao: Classificacao


def calcular(inscricao: Inscricao, janela: Janela = "acumulado") -> InscricaoCalculada:
    """Média, frequência e classificação de uma inscrição, na janela pedida."""

    def media_de(periodo: str | None) -> Decimal | None:
        return media_ponderada(
            (a.nota, a.peso)
            for a in inscricao.avaliacoes
            if periodo is None or a.periodo_avaliacao == periodo
        )

    def presenca_de(periodo: str | None) -> tuple[int, int]:
        lancadas = [
            f for f in inscricao.frequencias if periodo is None or f.periodo_avaliacao == periodo
        ]
        return sum(f.aulas_previstas for f in lancadas), sum(f.faltas for f in lancadas)

    filtro = None if janela == "acumulado" else janela
    aulas, faltas = presenca_de(filtro)
    media = media_de(filtro)
    frequencia = percentual_de_frequencia(aulas, faltas)
    return InscricaoCalculada(
        inscricao=inscricao,
        nota_n1=media_de("N1"),
        nota_n2=media_de("N2"),
        media=media,
        media_n1=media_de("N1"),
        frequencia=frequencia,
        frequencia_n1=percentual_de_frequencia(*presenca_de("N1")),
        aulas=aulas,
        faltas=faltas,
        classificacao=classificar(inscricao.disciplina.nome, media, frequencia),
    )


def que_contam(inscricoes: Iterable[Inscricao]) -> list[Inscricao]:
    return [i for i in inscricoes if i.status in STATUS_QUE_CONTAM]


def _media_simples(valores: Iterable[Decimal | None]) -> Decimal | None:
    validos = [v for v in valores if v is not None]
    return arredondar(sum(validos, Decimal(0)) / len(validos)) if validos else None


def _rotulo_oferta(calculada: InscricaoCalculada) -> str:
    """ "EST A" a partir dos códigos "EST-2026.2-A" e "IA2-2026.2-A"; senão, o nome."""
    disciplina = calculada.inscricao.disciplina
    sigla = disciplina.codigo.split("-")[0] if disciplina.codigo else disciplina.nome
    turma = (
        disciplina.turma.codigo.split("-")[-1] if disciplina.turma.codigo else disciplina.turma.nome
    )
    return f"{sigla} {turma}"


def _histograma(calculadas: Sequence[InscricaoCalculada]) -> list[FaixaHistograma]:
    contagem = estatistica.histograma([c.media for c in calculadas if c.media is not None])
    return [FaixaHistograma(faixa=f"{i}–{i + 1}", inscricoes=n) for i, n in enumerate(contagem)]


def _projecoes(calculadas: list[InscricaoCalculada]) -> dict[int, Decimal]:
    """Média final projetada pela regressão, por inscrição (vazio se não houver modelo)."""
    modelo = predicao.ajustar(calculadas)
    if modelo is None:
        return {}
    return {
        p.calculada.inscricao.id: p.media_projetada for p in predicao.prever(modelo, calculadas)
    }


def _alunos(
    calculadas: Sequence[InscricaoCalculada], projecoes: dict[int, Decimal] | None = None
) -> list[AlunoPainel]:
    por_aluno: dict[int, list[InscricaoCalculada]] = {}
    for calculada in calculadas:
        por_aluno.setdefault(calculada.inscricao.aluno.id, []).append(calculada)

    alunos = []
    for lista in por_aluno.values():
        aluno = lista[0].inscricao.aluno
        status, atencao = consolidar(c.classificacao for c in lista)
        validas = [c for c in lista if c.classificacao.status != "indeterminado"]
        alunos.append(
            AlunoPainel(
                id=aluno.id,
                nome=aluno.nome_completo,
                matricula=aluno.matricula,
                turma_id=aluno.turma_id,
                turma_nome=lista[0].inscricao.disciplina.turma.nome,
                media=_media_simples(c.media for c in validas),
                frequencia=_media_simples(c.frequencia for c in validas),
                status=status,
                atencao=atencao,
                situacao=situacao(status, atencao),
                inscricoes=[
                    InscricaoPainel(
                        inscricao_id=c.inscricao.id,
                        disciplina_id=c.inscricao.disciplina.id,
                        disciplina_codigo=c.inscricao.disciplina.codigo,
                        disciplina_nome=c.inscricao.disciplina.nome,
                        nota_n1=c.nota_n1,
                        nota_n2=c.nota_n2,
                        media=c.media,
                        frequencia=c.frequencia,
                        aulas=c.aulas,
                        faltas=c.faltas,
                        status=c.classificacao.status,
                        atencao=c.classificacao.atencao,
                        situacao=c.classificacao.situacao,
                        criterios=list(c.classificacao.criterios),
                        justificativa=c.classificacao.justificativa,
                    )
                    for c in lista
                ],
                recomendacoes=[
                    RecomendacaoSaida.model_validate(r) for r in recomendar(lista, projecoes or {})
                ],
            )
        )
    return sorted(alunos, key=lambda a: a.nome)


def _contar(situacoes: Iterable[str]) -> dict[str, int]:
    contagem = Counter(situacoes)
    return {s: contagem.get(s, 0) for s in SITUACOES}


def montar_painel(inscricoes: Iterable[Inscricao]) -> Painel:
    calculadas = [calcular(i) for i in que_contam(inscricoes)]
    validas = [c for c in calculadas if c.classificacao.status != "indeterminado"]
    alunos = _alunos(calculadas, _projecoes(calculadas))
    contagem = _contar(a.situacao for a in alunos)

    ofertas: dict[str, list[InscricaoCalculada]] = {}
    for calculada in calculadas:
        ofertas.setdefault(_rotulo_oferta(calculada), []).append(calculada)
    situacao_por_oferta = [
        SituacaoOferta(
            oferta=rotulo,
            disciplina_id=lista[0].inscricao.disciplina.id,
            **_contar(c.classificacao.situacao for c in lista),
        )
        for rotulo, lista in sorted(ofertas.items())
    ]

    return Painel(
        total_alunos=len(alunos),
        total_inscricoes=len(calculadas),
        inscricoes_sem_dados=len(calculadas) - len(validas),
        media_geral=_media_simples(c.media for c in validas),
        media_n1=_media_simples(c.media_n1 for c in validas),
        frequencia_geral=_media_simples(c.frequencia for c in validas),
        frequencia_n1=_media_simples(c.frequencia_n1 for c in validas),
        contagem=contagem,
        histograma=_histograma(validas),
        dispersao=[
            PontoDispersao(
                aluno=c.inscricao.aluno.nome_completo,
                disciplina=c.inscricao.disciplina.nome,
                media=c.media,
                frequencia=c.frequencia,
                situacao=c.classificacao.situacao,
            )
            for c in validas
            if c.media is not None and c.frequencia is not None
        ],
        correlacao_frequencia_media=estatistica.correlacao(
            [c.frequencia for c in validas if c.frequencia is not None],
            [c.media for c in validas if c.media is not None],
        ),
        situacao_por_oferta=situacao_por_oferta,
        achados=[AchadoSaida.model_validate(a) for a in gerar_achados(calculadas, contagem)],
        alunos=alunos,
    )


def montar_indicadores(
    inscricoes: Iterable[Inscricao], recorte: str, janela: Janela
) -> Indicadores:
    """Indicadores de um recorte.

    A janela parcial (N1) é um subconjunto do semestre, então a variância é amostral (D07).
    """
    calculadas = [calcular(i, janela) for i in que_contam(inscricoes)]
    validas = [c for c in calculadas if c.classificacao.status != "indeterminado"]
    amostral = janela != "acumulado"
    medias = [c.media for c in validas if c.media is not None]
    frequencias = [c.frequencia for c in validas if c.frequencia is not None]

    por_disciplina: dict[int, list[InscricaoCalculada]] = {}
    for calculada in validas:
        por_disciplina.setdefault(calculada.inscricao.disciplina.id, []).append(calculada)
    ranking = [
        IndicadorDisciplina(
            disciplina_id=disciplina_id,
            oferta=_rotulo_oferta(lista[0]),
            disciplina=lista[0].inscricao.disciplina.nome,
            turma=lista[0].inscricao.disciplina.turma.nome,
            n=len(lista),
            media=_media_simples(c.media for c in lista),
            media_n1=_media_simples(c.media_n1 for c in lista),
            frequencia_media=_media_simples(c.frequencia for c in lista),
        )
        for disciplina_id, lista in por_disciplina.items()
    ]
    ranking.sort(key=lambda d: d.media or Decimal(0), reverse=True)
    situacao_alunos = _contar(a.situacao for a in _alunos(calculadas))

    return Indicadores(
        recorte=recorte,
        janela=janela,
        inscricoes_validas=len(validas),
        inscricoes_sem_dados=len(calculadas) - len(validas),
        media=ResumoEstatistico.model_validate(estatistica.resumir(medias, amostral=amostral)),
        frequencia=ResumoEstatistico.model_validate(
            estatistica.resumir(frequencias, amostral=amostral)
        ),
        correlacao_frequencia_media=estatistica.correlacao(
            [c.frequencia for c in validas if c.frequencia is not None and c.media is not None],
            [c.media for c in validas if c.frequencia is not None and c.media is not None],
        ),
        histograma=_histograma(validas),
        por_disciplina=ranking,
        situacao_alunos=situacao_alunos,
        situacao_inscricoes=_contar(c.classificacao.situacao for c in calculadas),
        achados=[AchadoSaida.model_validate(a) for a in gerar_achados(calculadas, situacao_alunos)],
    )


def montar_predicao(inscricoes: Iterable[Inscricao]) -> Predicao:
    """Regressão N2 ~ N1 + frequência N1 e projeção da média final de cada inscrição (D21)."""
    calculadas = [calcular(i) for i in que_contam(inscricoes)]
    modelo = predicao.ajustar(calculadas)
    if modelo is None:
        return Predicao(
            modelo=None,
            observacao=(
                f"São necessárias pelo menos {predicao.MINIMO_DE_OBSERVACOES} inscrições com N1, "
                "N2 e frequência lançadas para ajustar o modelo."
            ),
            previsoes=[],
            limites=predicao.LIMITES,
        )

    previsoes = [
        PrevisaoInscricao(
            inscricao_id=p.calculada.inscricao.id,
            aluno_id=p.calculada.inscricao.aluno.id,
            aluno=p.calculada.inscricao.aluno.nome_completo,
            matricula=p.calculada.inscricao.aluno.matricula,
            disciplina=_rotulo_oferta(p.calculada),
            nota_n1=p.calculada.nota_n1,
            frequencia_n1=p.calculada.frequencia_n1,
            nota_n2_prevista=p.nota_n2_prevista,
            nota_n2_real=p.calculada.nota_n2,
            media_projetada=p.media_projetada,
            media_real=p.calculada.media,
            situacao_atual=p.calculada.classificacao.situacao,
            risco_projetado=p.risco_projetado,
        )
        for p in predicao.prever(modelo, calculadas)
    ]
    previsoes.sort(key=lambda p: p.media_projetada)

    return Predicao(
        modelo=ModeloRegressao(
            equacao=predicao.descrever(modelo),
            variaveis=list(predicao.VARIAVEIS),
            coeficientes=list(modelo.coeficientes),
            n=modelo.n,
            r2=round(modelo.r2, 4),
            erro_medio=round(modelo.erro_medio, 4),
            erro_validacao=round(modelo.erro_validacao, 4),
            acerto_risco=round(modelo.acerto_risco, 1),
            interpretacao=predicao.interpretar(modelo),
        ),
        observacao=None,
        previsoes=previsoes,
        limites=predicao.LIMITES,
    )
