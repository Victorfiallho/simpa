"""Sinal de abandono silencioso: o aluno some e quase não entrega atividades (RF07).

Olha o registro semanal de presença e de atividades (acadêmico). Por disciplina:
  streak — semanas seguidas de ausência, contadas do fim do registro;
  req/ent — atividades previstas e entregues nas últimas 4 semanas registradas.

Uma disciplina tem o sinal quando a ausência dura 2 semanas ou mais e há atividade prevista:
  alto     — 3 semanas ou mais de ausência, nenhuma entrega e pelo menos 2 atividades previstas;
  atencao  — entregou 25% ou menos das previstas.
O alerta é do aluno, não de uma disciplina: sai quando metade ou mais das disciplinas com dados
tem o sinal.
"""

from dataclasses import dataclass
from math import ceil

from app.clientes.academico import Inscricao
from app.services.alertas_base import Sinal

SEMANAS_OLHADAS = 6
SEMANAS_DE_ATIVIDADE = 4
AUSENCIA_MINIMA = 2
AUSENCIA_GRAVE = 3
LIMITE_DE_ENTREGA = 0.25


@dataclass(frozen=True)
class SinalDisciplina:
    nivel: str
    ausencia: int
    previstas: int
    entregues: int


def _ordenadas(inscricao: Inscricao):
    return sorted(inscricao.semanas, key=lambda s: s.semana_inicio)


def semanas_seguidas_ausente(inscricao: Inscricao) -> int:
    seguidas = 0
    for semana in reversed(_ordenadas(inscricao)[-SEMANAS_OLHADAS:]):
        if semana.presente:
            break
        seguidas += 1
    return seguidas


def sinal_da_disciplina(inscricao: Inscricao) -> SinalDisciplina | None:
    ausencia = semanas_seguidas_ausente(inscricao)
    recentes = _ordenadas(inscricao)[-SEMANAS_DE_ATIVIDADE:]
    previstas = sum(s.atividades_previstas for s in recentes)
    entregues = sum(s.atividades_entregues for s in recentes)
    if ausencia < AUSENCIA_MINIMA or previstas <= 0:
        return None
    if ausencia >= AUSENCIA_GRAVE and entregues == 0 and previstas >= 2:
        nivel = "alto"
    elif entregues / previstas <= LIMITE_DE_ENTREGA:
        nivel = "atencao"
    else:
        return None
    return SinalDisciplina(nivel, ausencia, previstas, entregues)


def _sigla(inscricao: Inscricao) -> str:
    codigo = inscricao.disciplina.codigo
    return codigo.split("-")[0] if codigo else inscricao.disciplina.nome


def sinal_do_aluno(inscricoes: list[Inscricao]) -> Sinal | None:
    """`inscricoes` são as ativas ou concluídas de um mesmo aluno."""
    com_dados = [i for i in inscricoes if i.avaliacoes or i.frequencias]
    marcadas = [(i, s) for i in com_dados if (s := sinal_da_disciplina(i)) is not None]
    if not com_dados or len(marcadas) < max(1, ceil(len(com_dados) / 2)):
        return None
    graves = sum(1 for _, s in marcadas if s.nivel == "alto")
    ausencia = min(s.ausencia for _, s in marcadas)
    previstas = sum(s.previstas for _, s in marcadas)
    entregues = sum(s.entregues for _, s in marcadas)
    nivel = "alto" if graves > 0 and graves >= ceil(len(marcadas) / 2) else "atencao"
    siglas = ", ".join(_sigla(i) for i, _ in marcadas)
    return Sinal(
        tipo="abandono",
        nivel=nivel,
        titulo=f"Ausente há {ausencia} semana(s) seguidas e quase sem entregar atividades",
        detalhe=(
            f"{len(marcadas)} de {len(com_dados)} disciplina(s) com o sinal ({siglas}) · "
            f"{entregues} de {previstas} atividade(s) entregue(s) nas últimas "
            f"{SEMANAS_DE_ATIVIDADE} semanas"
        ),
        acao=(
            "Entrar em contato hoje, por telefone ou e-mail, e oferecer apoio antes de um "
            "possível trancamento ou desistência."
        ),
    )
