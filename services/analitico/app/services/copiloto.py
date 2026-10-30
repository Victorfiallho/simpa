"""Copiloto: responde perguntas em linguagem natural, por regras (RF07).

Não usa modelo de linguagem: reconhece a intenção por palavras-chave, acha a disciplina, a turma
ou o aluno citados e responde com os mesmos números do painel. Isso torna cada resposta
explicável e repetível. Quando não entende, diz o que sabe responder.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal

from app.clientes.academico import Inscricao
from app.schemas.copiloto import ItemResposta, RespostaCopiloto, SecaoResumo
from app.services.painel import InscricaoCalculada, calcular, que_contam
from app.services.regras import FREQUENCIA_MINIMA, formatar

LIMITE_MONITORIA = 10
LIMITE_FILTRO = 12
SUGESTOES = [
    "Quais alunos precisam de monitoria urgente?",
    "Gere um resumo do desempenho da turma para a reunião de colegiado",
    "Quem tirou abaixo de 5 em Estatística e tem presença menor que 70%?",
    "Quantos alunos estão em risco?",
]
AJUDA = (
    "Não entendi bem a pergunta. Posso ajudar com: alunos que precisam de monitoria ou apoio "
    "urgente; filtros por nota e frequência, por exemplo “abaixo de 5 e presença menor que "
    "70%”; a situação de um aluno pelo nome ou pela matrícula; contagens por situação; e um "
    "resumo do desempenho para o colegiado. Você pode citar a disciplina ou a turma."
)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-z0-9%.,\s-]", " ", sem_acento)
    return re.sub(r"\s+", " ", limpo).strip()


def _numero(texto: str) -> Decimal:
    return Decimal(texto.replace(",", "."))


@dataclass(frozen=True)
class Condicao:
    operador: str  # "<" ou ">"
    valor: Decimal


def condicao(n: str, palavras: str) -> Condicao | None:
    achou = re.search(
        rf"(?:{palavras})[^\d]{{0,30}}?(abaixo|menor|menos|inferior|acima|maior|mais|superior)"
        r"[^\d]{0,14}?(\d+(?:[.,]\d+)?)",
        n,
    )
    if not achou:
        return None
    menor = re.search(r"abaixo|menor|menos|inferior", achou.group(1))
    return Condicao("<" if menor else ">", _numero(achou.group(2)))


@dataclass
class Consulta:
    n: str
    disciplina_id: int | None = None
    disciplina_nome: str | None = None
    turma_id: int | None = None
    turma_nome: str | None = None
    desconhecido: str | None = None
    nota: Condicao | None = None
    frequencia: Condicao | None = None
    intencao: str | None = None
    aluno: "Inscricao | None" = field(default=None, repr=False)

    @property
    def recorte(self) -> str:
        return " · ".join(
            [self.turma_nome or "todas as turmas", self.disciplina_nome or "todas as disciplinas"]
        )


def _achar_disciplina(n: str, inscricoes: list[Inscricao]) -> Inscricao | None:
    for inscricao in inscricoes:
        d = inscricao.disciplina
        nome = normalizar(d.nome)
        codigo = normalizar(d.codigo or "")
        sigla = codigo.split("-")[0]  # "alg-2026.2-a" -> "alg"
        primeira = nome.split(" ")[0]
        if (
            (nome and nome in n)
            or (len(codigo) >= 2 and re.search(rf"\b{re.escape(codigo)}\b", n))
            or (len(sigla) >= 2 and re.search(rf"\b{re.escape(sigla)}\b", n))
            or (len(primeira) >= 6 and re.search(rf"\b{re.escape(primeira)}", n))
        ):
            return inscricao
    return None


def _achar_turma(n: str, inscricoes: list[Inscricao]) -> Inscricao | None:
    for inscricao in inscricoes:
        t = inscricao.disciplina.turma
        codigo = normalizar(t.codigo or "")
        if (normalizar(t.nome) and normalizar(t.nome) in n) or (
            len(codigo) >= 2 and re.search(rf"\b{re.escape(codigo)}\b", n)
        ):
            return inscricao
    return None


def _achar_aluno(n: str, inscricoes: list[Inscricao]) -> Inscricao | None:
    matricula = re.search(r"\b\d{6,12}\b", n)
    if matricula:
        return next((i for i in inscricoes if i.aluno.matricula == matricula.group()), None)
    melhor, pontos = None, 0
    vistos: set[int] = set()
    for inscricao in inscricoes:
        if inscricao.aluno.id in vistos:
            continue
        vistos.add(inscricao.aluno.id)
        partes = [t for t in normalizar(inscricao.aluno.nome_completo).split() if len(t) >= 3]
        acertos = sum(1 for t in partes if re.search(rf"\b{re.escape(t)}\b", n))
        if acertos > pontos:
            melhor, pontos = inscricao, acertos
    return melhor if pontos >= 2 else None


def interpretar(pergunta: str, inscricoes: list[Inscricao]) -> Consulta:
    n = normalizar(pergunta)
    consulta = Consulta(
        n=n,
        nota=condicao(n, "tirou|nota|notas|media"),
        frequencia=condicao(n, "presenca|frequencia|assiduidade"),
    )
    por_disciplina = _achar_disciplina(n, inscricoes)
    if por_disciplina:
        consulta.disciplina_id = por_disciplina.disciplina.id
        consulta.disciplina_nome = por_disciplina.disciplina.nome
    por_turma = _achar_turma(n, inscricoes)
    if por_turma:
        consulta.turma_id = por_turma.disciplina.turma.id
        consulta.turma_nome = por_turma.disciplina.turma.nome

    if not consulta.disciplina_id and not consulta.turma_id:
        achou = re.search(
            r"alunos? d[eoa]s? (?:curso de )?([a-z ]{4,40}?) "
            r"(?:precis|que |com |tem |estao|em risco|na |no |para )",
            n,
        ) or re.search(r" em ([a-z ]{4,40}?)(?: e (?:tem|com|que|esta)|$)", n)
        ignorar = (
            r"^(turma|disciplina|curso|risco|hoje|atencao|todas|todos|geral|recuperacao"
            r"|alerta|situacao)"
        )
        if achou and not re.match(ignorar, achou.group(1)):
            consulta.desconhecido = achou.group(1)

    consulta.aluno = _achar_aluno(n, inscricoes)
    if re.search(r"resum|colegiado|panorama|relatorio d|reuniao", n):
        consulta.intencao = "resumo"
    elif consulta.aluno is not None or re.search(r"\b\d{6,12}\b", n):
        # Uma matrícula na pergunta é sempre uma consulta de aluno, mesmo que ela não exista.
        consulta.intencao = "aluno"
    elif consulta.nota or consulta.frequencia:
        consulta.intencao = "filtro"
    elif re.search(r"monitoria|urgen|precisam de apoio|precisam de ajuda|priorid", n):
        consulta.intencao = "monitoria"
    elif re.search(
        r"alerta|abandono|queda|desist|tranc|evasao|projec|retenc|aprovad|aprovac|reprov|recuperac|passar|passam",
        n,
    ):
        consulta.intencao = "fora_do_escopo"
    elif re.search(r"quantos|quantas|quantidade|total|numero de", n):
        consulta.intencao = "contagem"
    elif re.search(r"(quem|quais|alunos?).*(risco|atencao)", n):
        consulta.intencao = "monitoria"
    elif re.search(r"risco|atencao|situacao|como est|desempenho|media|frequencia", n):
        consulta.intencao = "situacao"
    return consulta


# ---------- Cálculos sobre o recorte ----------


def _recorte(inscricoes: list[Inscricao], c: Consulta) -> list[InscricaoCalculada]:
    return [
        calcular(i)
        for i in que_contam(inscricoes)
        if i.aluno.status == "ativo"
        and (c.disciplina_id is None or i.disciplina.id == c.disciplina_id)
        and (c.turma_id is None or i.disciplina.turma.id == c.turma_id)
    ]


def _fmt(valor: Decimal | None, sufixo: str = "") -> str:
    return "—" if valor is None else f"{formatar(valor)}{sufixo}"


def _situacao_do_aluno(calculadas: list[InscricaoCalculada]) -> str:
    """Em risco se qualquer inscrição estiver em risco (D04); atenção; sem risco; indeterminado."""
    situacoes = {c.classificacao.situacao for c in calculadas}
    for situacao in ("em_risco", "atencao", "sem_risco"):
        if situacao in situacoes:
            return situacao
    return "indeterminado"


def _por_aluno(calculadas: list[InscricaoCalculada]) -> dict[int, list[InscricaoCalculada]]:
    grupos: dict[int, list[InscricaoCalculada]] = {}
    for c in calculadas:
        grupos.setdefault(c.inscricao.aluno.id, []).append(c)
    return grupos


def _urgencia(calculadas: list[InscricaoCalculada]) -> int:
    pontos = 0
    for c in calculadas:
        if c.classificacao.situacao == "em_risco":
            pontos += 1
        if c.media is not None and c.media < Decimal(5):
            pontos += 2
        if c.frequencia is not None and c.frequencia < FREQUENCIA_MINIMA:
            pontos += 2
    return pontos


def _item(c: InscricaoCalculada, detalhe: str) -> ItemResposta:
    aluno = c.inscricao.aluno
    return ItemResposta(
        aluno_id=aluno.id,
        aluno_nome=aluno.nome_completo,
        matricula=aluno.matricula,
        detalhe=detalhe,
    )


def _resposta(consulta: Consulta, texto: str, **extras) -> RespostaCopiloto:
    return RespostaCopiloto(
        intencao=consulta.intencao or "ajuda",  # type: ignore[arg-type]
        recorte=consulta.recorte,
        texto=texto,
        **extras,
    )


# ---------- Respostas ----------


def _monitoria(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    grupos = _por_aluno(_recorte(inscricoes, c))
    em_risco = {
        aluno: lista
        for aluno, lista in grupos.items()
        if any(x.classificacao.situacao == "em_risco" for x in lista)
    }
    if not em_risco:
        return _resposta(
            c, f"Nenhum aluno em risco em {c.recorte}. Não há monitoria urgente neste recorte."
        )
    ordenados = sorted(
        em_risco.values(),
        key=lambda lista: (-_urgencia(lista), lista[0].inscricao.aluno.nome_completo.casefold()),
    )
    itens = []
    for lista in ordenados[:LIMITE_MONITORIA]:
        trechos = [
            f"{x.inscricao.disciplina.nome} {_fmt(x.media)} · {_fmt(x.frequencia, '%')}"
            for x in lista
            if x.classificacao.situacao == "em_risco"
        ]
        itens.append(_item(lista[0], "; ".join(trechos)))
    por_disciplina: dict[str, int] = {}
    for lista in ordenados:
        for x in lista:
            if x.classificacao.situacao == "em_risco":
                por_disciplina[x.inscricao.disciplina.nome] = (
                    por_disciplina.get(x.inscricao.disciplina.nome, 0) + 1
                )
    mais = ", ".join(
        f"{nome} ({n})" for nome, n in sorted(por_disciplina.items(), key=lambda p: -p[1])[:3]
    )
    texto = (
        f"Encontrei {len(ordenados)} aluno(s) em risco em {c.recorte}. Priorizei pela gravidade: "
        f"média e frequência abaixo do mínimo."
    )
    if mais:
        texto += f" Disciplinas com mais risco: {mais}."
    return _resposta(c, texto, itens=itens, total_itens=len(ordenados))


def _filtro(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    def passa(valor: Decimal, cond: Condicao) -> bool:
        return valor < cond.valor if cond.operador == "<" else valor > cond.valor

    achadas = [
        x
        for x in _recorte(inscricoes, c)
        if x.media is not None
        and x.frequencia is not None
        and (c.nota is None or passa(x.media, c.nota))
        and (c.frequencia is None or passa(x.frequencia, c.frequencia))
    ]
    achadas.sort(key=lambda x: (x.media, x.inscricao.aluno.nome_completo.casefold()))
    partes = []
    if c.nota:
        partes.append(
            f"média {'abaixo' if c.nota.operador == '<' else 'acima'} de {formatar(c.nota.valor)}"
        )
    if c.frequencia:
        partes.append(
            f"frequência {'abaixo' if c.frequencia.operador == '<' else 'acima'} de "
            f"{formatar(c.frequencia.valor).removesuffix(',00')}%"
        )
    condicoes = " e ".join(partes)
    if not achadas:
        return _resposta(c, f"Nenhuma inscrição com {condicoes} em {c.recorte}.")
    itens = [
        _item(
            x, f"{x.inscricao.disciplina.nome}: média {_fmt(x.media)} · {_fmt(x.frequencia, '%')}"
        )
        for x in achadas[:LIMITE_FILTRO]
    ]
    return _resposta(
        c,
        f"{len(achadas)} inscrição(ões) com {condicoes} em {c.recorte}:",
        itens=itens,
        total_itens=len(achadas),
    )


def _aluno(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    if c.aluno is None:
        return _resposta(c, "Não encontrei esse aluno. Informe o nome completo ou a matrícula.")
    aluno = c.aluno.aluno
    rotulos = {
        "em_risco": "em risco",
        "atencao": "em atenção",
        "sem_risco": "sem risco",
        "indeterminado": "indeterminado",
    }
    do_aluno = [
        calcular(i)
        for i in que_contam(inscricoes)
        if i.aluno.id == aluno.id and aluno.status == "ativo"
    ]
    if aluno.status != "ativo":
        return _resposta(
            c,
            f"{aluno.nome_completo} ({aluno.matricula}) está com cadastro {aluno.status} e não "
            "entra nos indicadores.",
        )
    itens = [
        _item(
            x,
            f"{x.inscricao.disciplina.nome}: média {_fmt(x.media)} · {_fmt(x.frequencia, '%')} "
            f"· {rotulos[x.classificacao.situacao]}",
        )
        for x in do_aluno
    ]
    texto = (
        f"{aluno.nome_completo} ({aluno.matricula}): situação "
        f"{rotulos[_situacao_do_aluno(do_aluno)]}, em {len(do_aluno)} disciplina(s)."
    )
    return _resposta(c, texto, itens=itens, total_itens=len(itens))


def _contagem(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    grupos = _por_aluno(_recorte(inscricoes, c))
    situacoes = [_situacao_do_aluno(lista) for lista in grupos.values()]
    n = situacoes.count
    texto = (
        f"Em {c.recorte} há {len(grupos)} alunos ativos: {n('em_risco')} em risco, "
        f"{n('atencao')} em atenção, {n('sem_risco')} sem risco e {n('indeterminado')} "
        "indeterminado(s)."
    )
    return _resposta(c, texto)


def _media_simples(valores: list[Decimal]) -> Decimal | None:
    return sum(valores, Decimal(0)) / len(valores) if valores else None


def _situacao(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    calculadas = _recorte(inscricoes, c)
    grupos = _por_aluno(calculadas)
    situacoes = [_situacao_do_aluno(lista) for lista in grupos.values()]
    media = _media_simples([x.media for x in calculadas if x.media is not None])
    freq = _media_simples([x.frequencia for x in calculadas if x.frequencia is not None])
    texto = (
        f"Em {c.recorte}: média geral {_fmt(media)}, frequência média {_fmt(freq, '%')}, "
        f"{situacoes.count('em_risco')} aluno(s) em risco e "
        f"{situacoes.count('atencao')} em atenção."
    )
    return _resposta(c, texto)


def _resumo(inscricoes: list[Inscricao], c: Consulta) -> RespostaCopiloto:
    calculadas = _recorte(inscricoes, c)
    grupos = _por_aluno(calculadas)
    situacoes = [_situacao_do_aluno(lista) for lista in grupos.values()]
    total = len(grupos) or 1
    media = _media_simples([x.media for x in calculadas if x.media is not None])
    freq = _media_simples([x.frequencia for x in calculadas if x.frequencia is not None])

    def parte(chave: str) -> str:
        qtd = situacoes.count(chave)
        return f"{qtd} ({round(qtd * 100 / total)}%)"

    secoes = [
        SecaoResumo(
            titulo="Visão geral",
            linhas=[
                f"{len(grupos)} alunos ativos e {len(calculadas)} inscrições.",
                f"Média geral {_fmt(media)} e frequência média {_fmt(freq, '%')}.",
            ],
        ),
        SecaoResumo(
            titulo="Situação dos alunos",
            linhas=[
                f"Em risco: {parte('em_risco')}. Em atenção: {parte('atencao')}. "
                f"Sem risco: {parte('sem_risco')}. "
                f"Indeterminado: {situacoes.count('indeterminado')}."
            ],
        ),
    ]
    por_disciplina: dict[str, list[InscricaoCalculada]] = {}
    for x in calculadas:
        por_disciplina.setdefault(x.inscricao.disciplina.nome, []).append(x)
    linhas_disc = []
    ranking = []
    for nome, lista in por_disciplina.items():
        m = _media_simples([x.media for x in lista if x.media is not None])
        f = _media_simples([x.frequencia for x in lista if x.frequencia is not None])
        risco = sum(1 for x in lista if x.classificacao.situacao == "em_risco")
        if m is not None:
            ranking.append((m, nome, risco))
        linhas_disc.append(
            (
                m if m is not None else Decimal(99),
                f"{nome}: média {_fmt(m)}, frequência {_fmt(f, '%')}, {risco} de {len(lista)} "
                "inscrições em risco.",
            )
        )
    if linhas_disc:
        secoes.append(
            SecaoResumo(
                titulo="Desempenho por disciplina (da menor para a maior média)",
                linhas=[linha for _, linha in sorted(linhas_disc, key=lambda p: p[0])],
            )
        )
    prioritarios = sorted(
        (lista for lista in grupos.values() if _situacao_do_aluno(lista) == "em_risco"),
        key=lambda lista: (-_urgencia(lista), lista[0].inscricao.aluno.nome_completo.casefold()),
    )[:5]
    if prioritarios:
        secoes.append(
            SecaoResumo(
                titulo="Alunos prioritários",
                linhas=[
                    f"{lista[0].inscricao.aluno.nome_completo} "
                    f"({lista[0].inscricao.aluno.matricula}): "
                    + "; ".join(
                        f"{x.inscricao.disciplina.nome} média {_fmt(x.media)}, "
                        f"frequência {_fmt(x.frequencia, '%')}"
                        for x in lista
                        if x.classificacao.situacao == "em_risco"
                    )
                    + "."
                    for lista in prioritarios
                ],
            )
        )
    encaminhamentos = []
    if ranking:
        menor = min(ranking)
        if menor[2]:
            encaminhamentos.append(
                f"Oferecer monitoria em {menor[1]}, a disciplina de menor média."
            )
    baixa_freq = sum(
        1 for x in calculadas if x.frequencia is not None and x.frequencia < FREQUENCIA_MINIMA
    )
    if baixa_freq:
        encaminhamentos.append(
            f"Orientar {baixa_freq} inscrição(ões) com frequência abaixo de 75%."
        )
    encaminhamentos.append("Revisar com os professores as quedas bruscas entre a N1 e a N2.")
    secoes.append(SecaoResumo(titulo="Encaminhamentos sugeridos", linhas=encaminhamentos))

    completo = "\n".join(
        [f"RESUMO DO DESEMPENHO PARA O COLEGIADO\nRecorte: {c.recorte}"]
        + [
            f"\n{s.titulo.upper()}\n" + "\n".join(f"- {linha}" for linha in s.linhas)
            for s in secoes
        ]
    )
    return _resposta(
        c,
        f"Resumo do desempenho para o colegiado ({c.recorte}).",
        secoes=secoes,
        texto_completo=completo,
    )


def responder(pergunta: str, inscricoes: list[Inscricao]) -> RespostaCopiloto:
    consulta = interpretar(pergunta, inscricoes)
    if consulta.desconhecido:
        consulta.intencao = "desconhecido"
        disciplinas = sorted({i.disciplina.nome for i in inscricoes})
        return _resposta(
            consulta,
            f"Não encontrei “{consulta.desconhecido}” nos cadastros. Disciplinas: "
            f"{', '.join(disciplinas) or 'nenhuma'}.",
            sugestoes=SUGESTOES,
        )
    respondedores = {
        "resumo": _resumo,
        "aluno": _aluno,
        "filtro": _filtro,
        "monitoria": _monitoria,
        "contagem": _contagem,
        "situacao": _situacao,
    }
    if consulta.intencao == "fora_do_escopo":
        return _resposta(
            consulta,
            "Ainda não respondo sobre alertas precoces e projeção de aprovação por aqui. "
            "Use as abas Alertas e Cenários.",
            sugestoes=SUGESTOES,
        )
    if consulta.intencao not in respondedores:
        consulta.intencao = "ajuda"
        return _resposta(consulta, AJUDA, sugestoes=SUGESTOES)
    return respondedores[consulta.intencao](inscricoes, consulta)
