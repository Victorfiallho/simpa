"""Alertas precoces: sinais calculados na hora a partir das notas e faltas (RF07).

Três sinais, os mesmos do protótipo:
  queda      — a nota cai entre a N1 e a N2;
  frequencia — as faltas se aproximam do limite de 25% das aulas já registradas;
  abandono   — ausência seguida e quase nenhuma atividade entregue (ver abandono.py).


Só o atendimento (pendente, em acompanhamento, encerrado) é gravado. O alerta em si é derivado.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes.academico import Inscricao
from app.models import Acompanhamento, AtendimentoAlerta
from app.schemas.alertas import AlertaSaida, ListaAlertas, ResumoTipo
from app.services import abandono
from app.services.alertas_base import Sinal
from app.services.painel import calcular, que_contam
from app.services.regras import formatar

TIPOS = ("queda", "frequencia", "abandono")  # ordem do resumo
ORDEM_NA_LISTA = ("abandono", "queda", "frequencia")  # empate de gravidade: abandono primeiro
RANK = {"atencao": 1, "alto": 2}
LIMITE_DE_FALTAS = 25  # % das aulas registradas; equivale à frequência mínima de 75%
LIMITE_QUEDA_GRAVE = Decimal("0.30")
LIMITE_QUEDA = Decimal("0.20")
NOTA_BOA = Decimal("7.00")
MARGEM_CRITICA = 2
SEM_DISCIPLINA = 0  # o alerta de abandono é do aluno, não de uma disciplina


def _por_aluno(inscricoes: list[Inscricao]) -> dict[int, list[Inscricao]]:
    grupos: dict[int, list[Inscricao]] = {}
    for inscricao in inscricoes:
        grupos.setdefault(inscricao.aluno.id, []).append(inscricao)
    return grupos


def sinal_de_queda(nome_disciplina: str, n1: Decimal | None, n2: Decimal | None) -> Sinal | None:
    if n1 is None or n2 is None or n1 <= 0:
        return None
    queda = (n1 - n2) / n1
    if not (queda > LIMITE_QUEDA_GRAVE or (queda > LIMITE_QUEDA and n1 >= NOTA_BOA)):
        return None
    grave = queda > LIMITE_QUEDA_GRAVE and n1 >= NOTA_BOA
    return Sinal(
        tipo="queda",
        nivel="alto" if grave else "atencao",
        titulo=f"Queda de {round(queda * 100)}% entre a N1 e a N2",
        detalhe=f"{nome_disciplina}: N1 {formatar(n1)} → N2 {formatar(n2)}",
        acao=(
            "Conversar com o aluno e revisar o que mudou na N2: "
            "conteúdo, faltas ou uma dificuldade pontual."
        ),
    )


def sinal_de_frequencia(nome_disciplina: str, aulas: int, faltas: int) -> Sinal | None:
    if aulas <= 0:
        return None
    maximo = aulas * LIMITE_DE_FALTAS // 100
    restantes = maximo - faltas
    if restantes > MARGEM_CRITICA:
        return None
    frequencia = Decimal(aulas - faltas) * 100 / aulas
    if restantes < 0:
        titulo = f"Frequência abaixo de 75% ({formatar(frequencia)}%)"
        acao = "Registrar a situação e orientar o aluno sobre as opções de regularização."
    elif restantes == 0:
        titulo = "Sem margem: a próxima falta reprova por frequência"
        acao = "Avisar o aluno agora: a próxima falta compromete a aprovação por frequência."
    else:
        titulo = f"Margem crítica: restam {restantes} falta(s)"
        acao = "Avisar o aluno agora: a próxima falta compromete a aprovação por frequência."
    return Sinal(
        tipo="frequencia",
        nivel="alto" if restantes <= 0 else "atencao",
        titulo=titulo,
        detalhe=(
            f"{nome_disciplina}: {faltas} falta(s) em {aulas} aulas registradas, "
            f"limite de {maximo} sobre elas · frequência {formatar(frequencia)}%"
        ),
        acao=acao,
    )


def sinais_da_inscricao(inscricao: Inscricao) -> list[Sinal]:
    calculada = calcular(inscricao)
    nome = inscricao.disciplina.nome
    encontrados = [
        sinal_de_queda(nome, calculada.nota_n1, calculada.nota_n2),
        sinal_de_frequencia(nome, calculada.aulas, calculada.faltas),
    ]
    return [s for s in encontrados if s is not None]


def _atendimentos(db: Session) -> dict[tuple[int, str, int], AtendimentoAlerta]:
    linhas = db.scalars(select(AtendimentoAlerta)).all()
    return {(a.aluno_id, a.tipo, a.disciplina_id): a for a in linhas}


def estado_efetivo(atendimento: AtendimentoAlerta | None, nivel_atual: str) -> str:
    """Um alerta que piorou depois de tratado volta a ser pendente."""
    if atendimento is None or RANK[nivel_atual] > RANK[atendimento.nivel]:
        return "pendente"
    return atendimento.estado


def _ultimo_contato(db: Session) -> dict[int, str]:
    """Texto do último acompanhamento de cada aluno, como no protótipo."""
    rotulos = {"contato": "Contato realizado", "orientacao": "Orientação", "monitoria": "Monitoria"}
    ultimos: dict[int, Acompanhamento] = {}
    consulta = select(Acompanhamento).order_by(Acompanhamento.data, Acompanhamento.id)
    for linha in db.scalars(consulta):
        ultimos[linha.aluno_id] = linha
    return {
        aluno: f"Último contato: {a.data:%d/%m/%Y} · {rotulos[a.tipo]}"
        for aluno, a in ultimos.items()
    }


def montar_alertas(db: Session, inscricoes: list[Inscricao]) -> list[AlertaSaida]:
    """Todos os alertas ativos das inscrições, do mais grave ao menos grave.

    Alunos inativos e inscrições trancadas ou canceladas não geram alerta. Os encerrados
    ficam por último.
    """
    atendimentos = _atendimentos(db)
    contatos = _ultimo_contato(db)
    saida: list[AlertaSaida] = []
    validas = que_contam(inscricoes)
    for aluno_id, do_aluno in _por_aluno(validas).items():
        aluno = do_aluno[0].aluno
        if aluno.status != "ativo":
            continue
        sinal_aluno = abandono.sinal_do_aluno(do_aluno)
        if sinal_aluno is not None:
            saida.append(
                AlertaSaida(
                    aluno_id=aluno.id,
                    aluno_nome=aluno.nome_completo,
                    matricula=aluno.matricula,
                    disciplina_id=SEM_DISCIPLINA,
                    disciplina_nome="Todas as disciplinas",
                    professor_id=None,
                    tipo=sinal_aluno.tipo,  # type: ignore[arg-type]
                    nivel=sinal_aluno.nivel,  # type: ignore[arg-type]
                    titulo=sinal_aluno.titulo,
                    detalhe=sinal_aluno.detalhe,
                    acao_sugerida=sinal_aluno.acao,
                    estado=estado_efetivo(
                        atendimentos.get((aluno_id, sinal_aluno.tipo, SEM_DISCIPLINA)),
                        sinal_aluno.nivel,
                    ),
                    ultimo_contato=contatos.get(aluno.id, "Sem acompanhamento registrado"),
                )
            )
    for inscricao in validas:
        aluno = inscricao.aluno
        if aluno.status != "ativo":
            continue
        for sinal in sinais_da_inscricao(inscricao):
            chave = (aluno.id, sinal.tipo, inscricao.disciplina.id)
            saida.append(
                AlertaSaida(
                    aluno_id=aluno.id,
                    aluno_nome=aluno.nome_completo,
                    matricula=aluno.matricula,
                    disciplina_id=inscricao.disciplina.id,
                    disciplina_nome=inscricao.disciplina.nome,
                    professor_id=inscricao.disciplina.professor_id,
                    tipo=sinal.tipo,
                    nivel=sinal.nivel,
                    titulo=sinal.titulo,
                    detalhe=sinal.detalhe,
                    acao_sugerida=sinal.acao,
                    estado=estado_efetivo(atendimentos.get(chave), sinal.nivel),
                    ultimo_contato=contatos.get(aluno.id, "Sem acompanhamento registrado"),
                )
            )
    saida.sort(
        key=lambda a: (
            a.estado == "encerrado",
            -RANK[a.nivel],
            ORDEM_NA_LISTA.index(a.tipo),
            a.aluno_nome.casefold(),
        )
    )
    return saida


def resumir(alertas: list[AlertaSaida]) -> list[ResumoTipo]:
    return [
        ResumoTipo(
            tipo=tipo,  # type: ignore[arg-type]
            total=sum(1 for a in alertas if a.tipo == tipo),
            graves=sum(1 for a in alertas if a.tipo == tipo and a.nivel == "alto"),
            pendentes=sum(1 for a in alertas if a.tipo == tipo and a.estado == "pendente"),
        )
        for tipo in TIPOS
    ]


def listar(
    db: Session,
    inscricoes: list[Inscricao],
    *,
    tipo: str | None = None,
    nivel: str | None = None,
    estado: str | None = None,
) -> ListaAlertas:
    todos = montar_alertas(db, inscricoes)
    filtrados = [
        a
        for a in todos
        if (tipo is None or a.tipo == tipo)
        and (nivel is None or a.nivel == nivel)
        and (estado is None or a.estado == estado)
    ]
    return ListaAlertas(resumo=resumir(todos), alertas=filtrados)


def gravar_estado(
    db: Session, alerta: AlertaSaida, estado: str, usuario_id: int
) -> AtendimentoAlerta:
    """Grava a situação do atendimento de um alerta ativo. Quem chama confirma a transação."""
    atual = db.scalar(
        select(AtendimentoAlerta).where(
            AtendimentoAlerta.aluno_id == alerta.aluno_id,
            AtendimentoAlerta.tipo == alerta.tipo,
            AtendimentoAlerta.disciplina_id == alerta.disciplina_id,
        )
    )
    if atual is None:
        atual = AtendimentoAlerta(
            aluno_id=alerta.aluno_id, tipo=alerta.tipo, disciplina_id=alerta.disciplina_id
        )
        db.add(atual)
    atual.estado = estado
    atual.nivel = alerta.nivel
    atual.atualizado_por = usuario_id
    return atual


def definir_estado(
    db: Session, alerta: AlertaSaida, estado: str, usuario_id: int
) -> AtendimentoAlerta:
    atendimento = gravar_estado(db, alerta, estado, usuario_id)
    db.commit()
    return atendimento
