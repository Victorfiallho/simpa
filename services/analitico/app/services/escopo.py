"""Escopo do professor (D03): só vê o risco e os indicadores das suas disciplinas.

`Disciplina.professor_id` guarda o id do usuário no auth (D13), o mesmo valor do `sub`.
Admin e coordenador enxergam tudo.
"""

from app.clientes.academico import Inscricao
from app.core.excecoes import AcessoNegado
from app.core.seguranca import UsuarioAtual


def filtrar_inscricoes(inscricoes: list[Inscricao], usuario: UsuarioAtual) -> list[Inscricao]:
    if usuario.role != "professor":
        return inscricoes
    return [i for i in inscricoes if i.disciplina.professor_id == usuario.id]


def garantir_disciplina_propria(professor_id: int | None, usuario: UsuarioAtual) -> None:
    if usuario.role == "professor" and professor_id != usuario.id:
        raise AcessoNegado(
            "Você só pode acessar as suas próprias disciplinas.",
            codigo="DISCIPLINA_FORA_DO_ESCOPO",
        )
