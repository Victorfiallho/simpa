"""Escopo do professor (D03): só enxerga e lança nas disciplinas em que é o responsável.

Admin e coordenador não têm restrição. Para o professor, `Disciplina.professor_id` guarda o
id do usuário no auth (D13), o mesmo valor do `sub` do token.
"""

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.core.excecoes import AcessoNegado
from app.core.seguranca import UsuarioAtual
from app.models import Disciplina, Inscricao

NEGADO = "Você só pode acessar as suas próprias disciplinas."


def restrito(usuario: UsuarioAtual) -> bool:
    return usuario.role == "professor"


def _ids_das_disciplinas(usuario: UsuarioAtual):
    return select(Disciplina.id).where(Disciplina.professor_id == usuario.id)


def condicao_disciplinas(usuario: UsuarioAtual) -> list[ColumnElement[bool]]:
    """Filtro para listar Disciplina; vazio quando o perfil não é restrito."""
    return [Disciplina.professor_id == usuario.id] if restrito(usuario) else []


def condicao_inscricoes(usuario: UsuarioAtual) -> list[ColumnElement[bool]]:
    """Filtro para listar Inscricao: só as das disciplinas do professor."""
    if not restrito(usuario):
        return []
    return [Inscricao.disciplina_id.in_(_ids_das_disciplinas(usuario))]


def condicao_por_inscricao(usuario: UsuarioAtual, coluna) -> list[ColumnElement[bool]]:
    """Filtro para Avaliacao/Frequencia: inscrição de uma disciplina do professor."""
    if not restrito(usuario):
        return []
    propria = select(Inscricao.id).where(
        Inscricao.disciplina_id.in_(_ids_das_disciplinas(usuario))
    )
    return [coluna.in_(propria)]


def condicao_alunos(usuario: UsuarioAtual, coluna_id) -> list[ColumnElement[bool]]:
    """Filtro para Aluno: tem inscrição numa disciplina do professor."""
    if not restrito(usuario):
        return []
    alunos = select(Inscricao.aluno_id).where(
        Inscricao.disciplina_id.in_(_ids_das_disciplinas(usuario))
    )
    return [coluna_id.in_(alunos)]


def garantir_disciplina_propria(disciplina: Disciplina, usuario: UsuarioAtual) -> None:
    if restrito(usuario) and disciplina.professor_id != usuario.id:
        raise AcessoNegado(NEGADO, codigo="DISCIPLINA_FORA_DO_ESCOPO")


def garantir_inscricao_propria(inscricao: Inscricao, usuario: UsuarioAtual) -> None:
    garantir_disciplina_propria(inscricao.disciplina, usuario)


def garantir_aluno_visivel(db: Session, aluno_id: int, usuario: UsuarioAtual) -> None:
    if not restrito(usuario):
        return
    consulta = (
        select(Inscricao.id)
        .where(
            Inscricao.aluno_id == aluno_id,
            Inscricao.disciplina_id.in_(_ids_das_disciplinas(usuario)),
        )
        .limit(1)
    )
    if db.scalar(consulta) is None:
        raise AcessoNegado(
            "Você só pode consultar alunos das suas disciplinas.", codigo="ALUNO_FORA_DO_ESCOPO"
        )
