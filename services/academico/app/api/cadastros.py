"""Rotas de turmas, disciplinas e alunos (RF01, RF02, RF04, RF08)."""

from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import or_

from app.api.dependencias import EXIGE_GESTOR, Gestor, Pagina, Sessao, Usuario
from app.core.respostas import Resposta, RespostaPaginada, resposta, resposta_paginada
from app.models import Aluno
from app.repositories.academico import AlunoRepositorio, DisciplinaRepositorio, TurmaRepositorio
from app.schemas.aluno import (
    AlunoAtualizacao,
    AlunoCriacao,
    AlunoDetalhado,
    AlunoLeitura,
    StatusAluno,
)
from app.schemas.disciplina import (
    DisciplinaAtualizacao,
    DisciplinaCriacao,
    DisciplinaLeitura,
    StatusDisciplina,
)
from app.schemas.turma import StatusTurma, TurmaAtualizacao, TurmaCriacao, TurmaLeitura
from app.services import cadastros, escopo

turmas = APIRouter(prefix="/turmas", tags=["Turmas"])
disciplinas = APIRouter(prefix="/disciplinas", tags=["Disciplinas"])
alunos = APIRouter(prefix="/alunos", tags=["Alunos"])

# ---------- Turmas ----------


@turmas.get("", response_model=RespostaPaginada[TurmaLeitura])
def listar_turmas(
    db: Sessao,
    pagina: Pagina,
    periodo_letivo: str | None = None,
    codigo: str | None = None,
    status_: Annotated[StatusTurma | None, Query(alias="status")] = None,
):
    itens, total = TurmaRepositorio(db).listar(
        pagina, {"periodo_letivo": periodo_letivo, "codigo": codigo, "status": status_}
    )
    return resposta_paginada(TurmaLeitura, itens, total, pagina.pagina, pagina.limite)


@turmas.get("/{turma_id}", response_model=Resposta[TurmaLeitura])
def obter_turma(turma_id: int, db: Sessao):
    return resposta(TurmaLeitura, TurmaRepositorio(db).obter_ou_falhar(turma_id))


@turmas.post(
    "",
    response_model=Resposta[TurmaLeitura],
    status_code=status.HTTP_201_CREATED,
    dependencies=[EXIGE_GESTOR],
)
def criar_turma(dados: TurmaCriacao, db: Sessao):
    return resposta(TurmaLeitura, cadastros.criar_turma(db, dados), "Turma cadastrada.")


@turmas.patch("/{turma_id}", response_model=Resposta[TurmaLeitura])
def atualizar_turma(turma_id: int, dados: TurmaAtualizacao, db: Sessao, usuario: Gestor):
    turma = cadastros.atualizar_turma(db, turma_id, dados, usuario)
    return resposta(TurmaLeitura, turma, "Turma atualizada.")


@turmas.delete("/{turma_id}", response_model=Resposta[TurmaLeitura], dependencies=[EXIGE_GESTOR])
def inativar_turma(turma_id: int, db: Sessao):
    return resposta(TurmaLeitura, cadastros.inativar_turma(db, turma_id), "Turma inativada.")


# ---------- Disciplinas ----------


@disciplinas.get("", response_model=RespostaPaginada[DisciplinaLeitura])
def listar_disciplinas(
    db: Sessao,
    pagina: Pagina,
    usuario: Usuario,
    turma_id: int | None = None,
    professor_id: int | None = None,
    periodo_letivo: str | None = None,
    status_: Annotated[StatusDisciplina | None, Query(alias="status")] = None,
):
    itens, total = DisciplinaRepositorio(db).listar(
        pagina,
        {
            "turma_id": turma_id,
            "professor_id": professor_id,
            "periodo_letivo": periodo_letivo,
            "status": status_,
        },
        escopo.condicao_disciplinas(usuario),
    )
    return resposta_paginada(DisciplinaLeitura, itens, total, pagina.pagina, pagina.limite)


@disciplinas.get("/{disciplina_id}", response_model=Resposta[DisciplinaLeitura])
def obter_disciplina(disciplina_id: int, db: Sessao, usuario: Usuario):
    disciplina = DisciplinaRepositorio(db).obter_ou_falhar(disciplina_id)
    escopo.garantir_disciplina_propria(disciplina, usuario)
    return resposta(DisciplinaLeitura, disciplina)


@disciplinas.post(
    "",
    response_model=Resposta[DisciplinaLeitura],
    status_code=status.HTTP_201_CREATED,
    dependencies=[EXIGE_GESTOR],
)
def criar_disciplina(dados: DisciplinaCriacao, db: Sessao):
    disciplina = cadastros.criar_disciplina(db, dados)
    return resposta(DisciplinaLeitura, disciplina, "Disciplina cadastrada.")


@disciplinas.patch("/{disciplina_id}", response_model=Resposta[DisciplinaLeitura])
def atualizar_disciplina(
    disciplina_id: int, dados: DisciplinaAtualizacao, db: Sessao, usuario: Gestor
):
    disciplina = cadastros.atualizar_disciplina(db, disciplina_id, dados, usuario)
    return resposta(DisciplinaLeitura, disciplina, "Disciplina atualizada.")


@disciplinas.delete(
    "/{disciplina_id}", response_model=Resposta[DisciplinaLeitura], dependencies=[EXIGE_GESTOR]
)
def inativar_disciplina(disciplina_id: int, db: Sessao):
    disciplina = cadastros.inativar_disciplina(db, disciplina_id)
    return resposta(DisciplinaLeitura, disciplina, "Disciplina inativada.")


# ---------- Alunos ----------


@alunos.get("", response_model=RespostaPaginada[AlunoLeitura])
def listar_alunos(
    db: Sessao,
    pagina: Pagina,
    usuario: Usuario,
    turma_id: int | None = None,
    status_: Annotated[StatusAluno | None, Query(alias="status")] = None,
    busca: Annotated[
        str | None, Query(min_length=2, max_length=60, description="Parte do nome ou da matrícula")
    ] = None,
):
    condicoes = escopo.condicao_alunos(usuario, Aluno.id)
    if busca:
        termo = f"%{busca}%"
        condicoes.append(or_(Aluno.nome_completo.ilike(termo), Aluno.matricula.ilike(termo)))
    itens, total = AlunoRepositorio(db).listar(
        pagina, {"turma_id": turma_id, "status": status_}, condicoes
    )
    return resposta_paginada(AlunoLeitura, itens, total, pagina.pagina, pagina.limite)


@alunos.get("/matricula/{matricula}", response_model=Resposta[AlunoDetalhado])
def consultar_aluno_por_matricula(matricula: str, db: Sessao, usuario: Usuario):
    """Consulta integrada pela matrícula (RF04)."""
    aluno = cadastros.consultar_aluno(db, matricula=matricula)
    escopo.garantir_aluno_visivel(db, aluno.id, usuario)
    return resposta(AlunoDetalhado, aluno)


@alunos.get("/{aluno_id}", response_model=Resposta[AlunoDetalhado])
def consultar_aluno(aluno_id: int, db: Sessao, usuario: Usuario):
    """Consulta integrada: cadastro, disciplinas, notas e frequências (RF04)."""
    escopo.garantir_aluno_visivel(db, aluno_id, usuario)
    return resposta(AlunoDetalhado, cadastros.consultar_aluno(db, aluno_id=aluno_id))


@alunos.post(
    "",
    response_model=Resposta[AlunoLeitura],
    status_code=status.HTTP_201_CREATED,
    dependencies=[EXIGE_GESTOR],
)
def criar_aluno(dados: AlunoCriacao, db: Sessao):
    return resposta(AlunoLeitura, cadastros.criar_aluno(db, dados), "Aluno cadastrado.")


@alunos.patch("/{aluno_id}", response_model=Resposta[AlunoLeitura], dependencies=[EXIGE_GESTOR])
def atualizar_aluno(aluno_id: int, dados: AlunoAtualizacao, db: Sessao):
    return resposta(
        AlunoLeitura, cadastros.atualizar_aluno(db, aluno_id, dados), "Aluno atualizado."
    )


@alunos.delete("/{aluno_id}", response_model=Resposta[AlunoLeitura], dependencies=[EXIGE_GESTOR])
def inativar_aluno(aluno_id: int, db: Sessao):
    return resposta(AlunoLeitura, cadastros.inativar_aluno(db, aluno_id), "Aluno inativado.")
