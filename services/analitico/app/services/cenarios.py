"""Cenários: simula regras de aprovação e calcula a margem de cada aluno (RF07).

Nada é gravado. As regras vêm na requisição e o resultado é calculado na hora, como no
protótipo. A projeção é uma estimativa, não uma previsão.

Regras ajustáveis (todas de 0 a 10):
    aprovacao   — média para aprovação direta (padrão 6)
    recuperacao — média mínima para fazer recuperação (padrão 4)
    final       — média final com recuperação: (média + exame) ÷ 2 (padrão 5)
A frequência mínima continua fixa em 75% (D05).
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import Literal

from app.clientes.academico import Inscricao
from app.core.excecoes import RegraDeNegocioViolada
from app.schemas.cenarios import (
    AlunosProjetados,
    ContagemProjetada,
    MargemSaida,
    OfertaProjetada,
    Projecao,
    RegrasSaida,
    VariacaoDisciplina,
)
from app.services.painel import calcular, que_contam
from app.services.regras import FREQUENCIA_MINIMA, arredondar, formatar

Base = Literal["n1", "atual"]
DEZ = Decimal(10)
PESO_PADRAO_N2 = Decimal(6)
CENTESIMO = Decimal("0.01")


@dataclass(frozen=True)
class Regras:
    aprovacao: Decimal = Decimal(6)
    recuperacao: Decimal = Decimal(4)
    final: Decimal = Decimal(5)

    def validar(self) -> None:
        valores = (self.aprovacao, self.recuperacao, self.final)
        if any(not (0 <= v <= DEZ) for v in valores) or self.recuperacao > self.aprovacao:
            raise RegraDeNegocioViolada(
                "Regras inválidas: use valores de 0 a 10, com a média de recuperação "
                "menor ou igual à de aprovação.",
                codigo="REGRAS_INVALIDAS",
            )


@dataclass(frozen=True)
class Dados:
    """O que se sabe de uma inscrição na base escolhida."""

    n1: Decimal | None
    peso1: Decimal
    n2: Decimal | None
    peso2: Decimal
    frequencia: Decimal | None


def _teto2(valor: Decimal) -> Decimal:
    """Arredonda para cima, em centésimos: a nota mínima nunca pode ficar abaixo do necessário."""
    return (valor / CENTESIMO).to_integral_value(rounding=ROUND_CEILING) * CENTESIMO


def dados_da_inscricao(inscricao: Inscricao, base: Base) -> Dados:
    calculada = calcular(inscricao, "N1" if base == "n1" else "acumulado")
    peso1 = sum((a.peso for a in inscricao.avaliacoes if a.periodo_avaliacao == "N1"), Decimal(0))
    peso2 = sum((a.peso for a in inscricao.avaliacoes if a.periodo_avaliacao == "N2"), Decimal(0))
    if base == "n1":
        return Dados(calculada.nota_n1, peso1, None, PESO_PADRAO_N2, calculada.frequencia_n1)
    return Dados(
        calculada.nota_n1,
        peso1,
        calculada.nota_n2,
        peso2 or PESO_PADRAO_N2,
        calculada.frequencia,
    )


def resultado_da_media(media: Decimal, frequencia: Decimal | None, regras: Regras) -> str:
    if frequencia is not None and frequencia < FREQUENCIA_MINIMA:
        return "rep_freq"
    if media >= regras.aprovacao:
        return "direta"
    if media >= regras.recuperacao:
        return "recuperacao"
    return "rep_nota"


@dataclass
class Margem:
    modo: str  # sem_dados | n2 | aprovado | exame | rep_nota
    n1: Decimal | None = None
    n2: Decimal | None = None
    media: Decimal | None = None
    frequencia: Decimal | None = None
    freq_reprova: bool = False
    necessario: Decimal | None = None
    media_maxima: Decimal | None = None
    exame_possivel: bool | None = None
    hipotese_media: Decimal | None = None
    hipotese_resultado: str | None = None


def calcular_margem(dados: Dados, regras: Regras, hipotese: Decimal | None = None) -> Margem:
    margem = Margem(
        modo="sem_dados",
        n1=dados.n1,
        n2=dados.n2,
        frequencia=dados.frequencia,
        freq_reprova=dados.frequencia is not None and dados.frequencia < FREQUENCIA_MINIMA,
    )
    if dados.n1 is None:
        return margem
    n1, w1, w2 = dados.n1, dados.peso1, dados.peso2

    if dados.n2 is None:
        precisa = (regras.aprovacao * (w1 + w2) - n1 * w1) / w2
        margem.modo = "n2"
        margem.media = n1
        margem.necessario = Decimal(0) if precisa <= 0 else _teto2(precisa)
        margem.media_maxima = arredondar((n1 * w1 + DEZ * w2) / (w1 + w2))
        if hipotese is not None:
            media = arredondar((n1 * w1 + hipotese * w2) / (w1 + w2))
            margem.hipotese_media = media
            margem.hipotese_resultado = resultado_da_media(media, dados.frequencia, regras)
        return margem

    media = arredondar((n1 * w1 + dados.n2 * w2) / (w1 + w2))
    margem.media = media
    if media >= regras.aprovacao:
        margem.modo = "aprovado"
    elif media >= regras.recuperacao:
        margem.modo = "exame"
        margem.necessario = _teto2(2 * regras.final - media)
        margem.exame_possivel = margem.necessario <= DEZ
        if hipotese is not None:
            final = arredondar((media + hipotese) / 2)
            margem.hipotese_media = final
            if margem.freq_reprova:
                margem.hipotese_resultado = "rep_freq"
            else:
                margem.hipotese_resultado = "recuperado" if final >= regras.final else "rep_nota"
    else:
        margem.modo = "rep_nota"
    return margem


def viabilidade(margem: Margem) -> tuple[int, str]:
    """(gravidade de 0 a 5, código). Mesma escala do protótipo."""
    if margem.modo == "aprovado":
        return 0, "aprovado_direto"
    if margem.freq_reprova:
        return 5, "reprovacao_frequencia"
    precisa = margem.necessario
    if margem.modo == "n2" and precisa is not None:
        if precisa == 0:
            return 0, "garantida"
        for limite, codigo, nivel in (
            (6, "alcancavel", 1),
            (8, "exige_esforco", 2),
            (10, "dificil", 3),
        ):
            if precisa <= limite:
                return nivel, codigo
        return 4, "inviavel"
    if margem.modo == "exame" and precisa is not None:
        for limite, codigo, nivel in (
            (5, "alcancavel", 1),
            (7, "exige_esforco", 2),
            (10, "dificil", 3),
        ):
            if precisa <= limite:
                return nivel, codigo
        return 4, "inviavel"
    if margem.modo == "rep_nota":
        return 5, "reprovacao_nota"
    return 0, "sem_dados"


def meta_em_texto(margem: Margem, regras: Regras) -> str:
    aviso = ""
    if margem.freq_reprova and margem.frequencia is not None:
        aviso = (
            f" Frequência de {formatar(margem.frequencia)}%, abaixo de 75%: "
            "reprovação por frequência mesmo com boa nota."
        )
    if margem.modo == "sem_dados":
        return "Sem notas lançadas."
    if margem.modo == "aprovado":
        return f"Média {formatar(margem.media)}: aprovado direto.{aviso}"
    if margem.modo == "n2":
        if margem.necessario == 0:
            return f"Já garante a aprovação direta, qualquer que seja a N2.{aviso}"
        if margem.necessario <= DEZ:
            return (
                f"Precisa de {formatar(margem.necessario)} na N2 para aprovar direto "
                f"(média {formatar(regras.aprovacao)}).{aviso}"
            )
        return (
            f"Mesmo com 10 na N2 a média máxima é {formatar(margem.media_maxima)}: "
            f"irá para recuperação.{aviso}"
        )
    if margem.modo == "exame":
        if margem.exame_possivel:
            return (
                f"Média {formatar(margem.media)}: recuperação. Precisa de "
                f"{formatar(margem.necessario)} no exame "
                f"(média final {formatar(regras.final)}).{aviso}"
            )
        return (
            f"Média {formatar(margem.media)}: nem 10 no exame recupera, pois exigiria "
            f"{formatar(margem.necessario)}.{aviso}"
        )
    return (
        f"Média {formatar(margem.media)}, abaixo de {formatar(regras.recuperacao)}: "
        f"reprovação por nota.{aviso}"
    )


def variacao_por_disciplina(inscricoes: list[Inscricao]) -> dict[int, Decimal]:
    """Variação média N2 − N1 de cada disciplina, usada para estimar a N2 de quem ainda não tem."""
    por_disciplina: dict[int, list[Decimal]] = {}
    for inscricao in inscricoes:
        calculada = calcular(inscricao)
        if calculada.nota_n1 is not None and calculada.nota_n2 is not None:
            por_disciplina.setdefault(inscricao.disciplina.id, []).append(
                calculada.nota_n2 - calculada.nota_n1
            )
    return {d: sum(v, Decimal(0)) / len(v) for d, v in por_disciplina.items()}


def projetar(
    inscricao: Inscricao, regras: Regras, base: Base, variacao: dict[int, Decimal]
) -> tuple[str, Margem]:
    """Categoria projetada da inscrição: direta, recuperacao, rep_nota, rep_freq ou sem_dados."""
    margem = calcular_margem(dados_da_inscricao(inscricao, base), regras)
    if margem.modo == "sem_dados":
        return "sem_dados", margem
    if margem.freq_reprova:
        return "rep_freq", margem
    media = margem.media
    if margem.modo == "n2":
        dados = dados_da_inscricao(inscricao, base)
        n2 = max(Decimal(0), min(DEZ, dados.n1 + variacao.get(inscricao.disciplina.id, Decimal(0))))
        media = arredondar(
            (dados.n1 * dados.peso1 + n2 * dados.peso2) / (dados.peso1 + dados.peso2)
        )
    return resultado_da_media(media, margem.frequencia, regras), margem


def inscricoes_validas(inscricoes: list[Inscricao]) -> list[Inscricao]:
    return [i for i in que_contam(inscricoes) if i.aluno.status == "ativo"]


def _margem_saida(inscricao: Inscricao, margem: Margem, regras: Regras) -> MargemSaida:
    gravidade, codigo = viabilidade(margem)
    return MargemSaida(
        inscricao_id=inscricao.id,
        aluno_id=inscricao.aluno.id,
        aluno_nome=inscricao.aluno.nome_completo,
        matricula=inscricao.aluno.matricula,
        disciplina_id=inscricao.disciplina.id,
        disciplina_nome=inscricao.disciplina.nome,
        modo=margem.modo,  # type: ignore[arg-type]
        n1=margem.n1,
        n2=margem.n2,
        media=margem.media,
        frequencia=margem.frequencia,
        necessario=margem.necessario,
        media_maxima=margem.media_maxima,
        viabilidade=codigo,
        gravidade=gravidade,
        meta=meta_em_texto(margem, regras),
        hipotese_media=margem.hipotese_media,
        hipotese_resultado=margem.hipotese_resultado,
    )


def margem_da_inscricao(
    inscricao: Inscricao, regras: Regras, base: Base, hipotese: Decimal | None
) -> MargemSaida:
    margem = calcular_margem(dados_da_inscricao(inscricao, base), regras, hipotese)
    return _margem_saida(inscricao, margem, regras)


def montar_projecao(
    inscricoes: list[Inscricao], regras: Regras, base: Base, limite_metas: int = 60
) -> Projecao:
    validas = inscricoes_validas(inscricoes)
    variacao = variacao_por_disciplina(validas)
    projetadas = [(i, *projetar(i, regras, base, variacao)) for i in validas]

    categorias = [categoria for _, categoria, _ in projetadas]
    contagem = ContagemProjetada(
        **{c: categorias.count(c) for c in ("direta", "recuperacao", "rep_nota", "rep_freq")},
        sem_dados=categorias.count("sem_dados"),
    )
    com_dados = len(categorias) - contagem.sem_dados
    nao_aprovadas = contagem.recuperacao + contagem.rep_nota + contagem.rep_freq

    pior_por_aluno: dict[int, int] = {}
    ordem = {"direta": 0, "recuperacao": 1, "rep_nota": 2, "rep_freq": 2}
    for inscricao, categoria, _ in projetadas:
        if categoria in ordem:
            atual = pior_por_aluno.get(inscricao.aluno.id, 0)
            pior_por_aluno[inscricao.aluno.id] = max(atual, ordem[categoria])
    pior = list(pior_por_aluno.values())

    ofertas: dict[str, OfertaProjetada] = {}
    for inscricao, categoria, _ in projetadas:
        if categoria == "sem_dados":
            continue
        disciplina = inscricao.disciplina
        rotulo = f"{disciplina.nome} · {disciplina.turma.codigo or disciplina.turma.nome}"
        oferta = ofertas.setdefault(
            rotulo, OfertaProjetada(oferta=rotulo, direta=0, recuperacao=0, rep_nota=0, rep_freq=0)
        )
        setattr(oferta, categoria, getattr(oferta, categoria) + 1)

    nomes = {i.disciplina.id: i.disciplina.nome for i in validas}
    em_risco = {
        i.aluno.id
        for i in validas
        if (c := calcular(i).classificacao).status == "em_risco" or c.atencao
    }
    metas = []
    for inscricao, _categoria, margem in projetadas:
        if inscricao.aluno.id not in em_risco or margem.modo in ("aprovado", "sem_dados"):
            continue
        metas.append(_margem_saida(inscricao, margem, regras))
    metas.sort(key=lambda m: (-m.gravidade, -(m.necessario or Decimal(0)), m.aluno_nome.casefold()))

    return Projecao(
        regras=RegrasSaida(
            aprovacao=regras.aprovacao, recuperacao=regras.recuperacao, final=regras.final
        ),
        base=base,
        inscricoes_projetadas=com_dados,
        contagem=contagem,
        retencao_percentual=(
            arredondar(Decimal(nao_aprovadas) * 100 / com_dados) if com_dados else None
        ),
        alunos=AlunosProjetados(
            aprovados_em_tudo=pior.count(0),
            com_recuperacao=pior.count(1),
            com_reprovacao=pior.count(2),
        ),
        por_oferta=sorted(ofertas.values(), key=lambda o: o.oferta),
        variacao_por_disciplina=[
            VariacaoDisciplina(disciplina_id=d, disciplina_nome=nomes[d], variacao=arredondar(v))
            for d, v in sorted(variacao.items())
            if d in nomes
        ],
        total_metas=len(metas),
        metas=metas[:limite_metas],
    )
