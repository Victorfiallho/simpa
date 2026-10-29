"""Casos de uso de turmas, disciplinas e alunos (RF01, RF02, RF04, D10).

Cada função é um caso de uso completo: valida, grava e faz um único commit no fim.
"""

from sqlalchemy.orm import Session

from app.clientes.auth import validar_professor
from app.core.excecoes import Conflito, RecursoNaoEncontrado
from app.core.seguranca import UsuarioAtual
from app.models import Aluno, Disciplina, Turma
from app.repositories.academico import AlunoRepositorio, DisciplinaRepositorio, TurmaRepositorio
from app.schemas.aluno import AlunoAtualizacao, AlunoCriacao
from app.schemas.disciplina import DisciplinaAtualizacao, DisciplinaCriacao
from app.schemas.turma import TurmaAtualizacao, TurmaCriacao
from app.services.comum import garantir_reabertura, mudancas, referencia

# ---------- Turmas ----------


def _codigo_livre(repositorio, modelo, codigo: str | None, id_atual: int | None = None) -> None:
    if codigo is None:
        return
    condicoes = [modelo.codigo == codigo]
    if id_atual is not None:
        condicoes.append(modelo.id != id_atual)
    if repositorio.existe(*condicoes):
        raise Conflito(f"Já existe um cadastro com o código {codigo}.", codigo="CODIGO_DUPLICADO")


def criar_turma(db: Session, dados: TurmaCriacao) -> Turma:
    repositorio = TurmaRepositorio(db)
    _codigo_livre(repositorio, Turma, dados.codigo)
    turma = repositorio.adicionar(Turma(**dados.model_dump()))
    db.commit()
    return turma


def atualizar_turma(
    db: Session, turma_id: int, dados: TurmaAtualizacao, usuario: UsuarioAtual
) -> Turma:
    repositorio = TurmaRepositorio(db)
    turma = repositorio.obter_ou_falhar(turma_id)
    alteracoes = mudancas(dados, aceitam_nulo={"codigo", "sala"})
    garantir_reabertura(turma.status, alteracoes.get("status"), usuario)
    if "codigo" in alteracoes:
        _codigo_livre(repositorio, Turma, alteracoes["codigo"], turma.id)
    repositorio.atualizar(turma, alteracoes)
    db.commit()
    return turma


def inativar_turma(db: Session, turma_id: int) -> Turma:
    repositorio = TurmaRepositorio(db)
    turma = repositorio.obter_ou_falhar(turma_id)
    if turma.status == "encerrada":
        raise Conflito("A turma está encerrada e não pode ser inativada.", codigo="TURMA_ENCERRADA")
    repositorio.atualizar(turma, {"status": "inativa"})
    db.commit()
    return turma


# ---------- Disciplinas ----------


def criar_disciplina(db: Session, dados: DisciplinaCriacao) -> Disciplina:
    repositorio = DisciplinaRepositorio(db)
    turma = referencia(TurmaRepositorio(db), dados.turma_id)
    if turma.status == "encerrada":
        raise Conflito("A turma está encerrada.", codigo="TURMA_ENCERRADA")
    _codigo_livre(repositorio, Disciplina, dados.codigo)
    if dados.professor_id is not None:
        validar_professor(dados.professor_id)
    disciplina = repositorio.adicionar(Disciplina(**dados.model_dump()))
    db.commit()
    return disciplina


def atualizar_disciplina(
    db: Session, disciplina_id: int, dados: DisciplinaAtualizacao, usuario: UsuarioAtual
) -> Disciplina:
    repositorio = DisciplinaRepositorio(db)
    disciplina = repositorio.obter_ou_falhar(disciplina_id)
    alteracoes = mudancas(dados, aceitam_nulo={"codigo", "professor_id"})
    garantir_reabertura(disciplina.status, alteracoes.get("status"), usuario)
    if "codigo" in alteracoes:
        _codigo_livre(repositorio, Disciplina, alteracoes["codigo"], disciplina.id)
    if alteracoes.get("professor_id") is not None:
        validar_professor(alteracoes["professor_id"])
    repositorio.atualizar(disciplina, alteracoes)
    db.commit()
    return disciplina


def inativar_disciplina(db: Session, disciplina_id: int) -> Disciplina:
    repositorio = DisciplinaRepositorio(db)
    disciplina = repositorio.obter_ou_falhar(disciplina_id)
    if disciplina.status == "encerrada":
        raise Conflito(
            "A disciplina está encerrada e não pode ser inativada.", codigo="DISCIPLINA_ENCERRADA"
        )
    repositorio.atualizar(disciplina, {"status": "inativa"})
    db.commit()
    return disciplina


# ---------- Alunos ----------


def _matricula_livre(repositorio: AlunoRepositorio, matricula: str) -> None:
    if repositorio.existe(Aluno.matricula == matricula):
        raise Conflito(f"A matrícula {matricula} já está cadastrada.", codigo="MATRICULA_DUPLICADA")


def _cpf_livre(repositorio: AlunoRepositorio, cpf: str | None, id_atual: int | None = None) -> None:
    if cpf is None:
        return
    condicoes = [Aluno.cpf == cpf]
    if id_atual is not None:
        condicoes.append(Aluno.id != id_atual)
    if repositorio.existe(*condicoes):
        raise Conflito("Este CPF já está cadastrado para outro aluno.", codigo="CPF_DUPLICADO")


def criar_aluno(db: Session, dados: AlunoCriacao) -> Aluno:
    repositorio = AlunoRepositorio(db)
    referencia(TurmaRepositorio(db), dados.turma_id)
    _matricula_livre(repositorio, dados.matricula)
    _cpf_livre(repositorio, dados.cpf)
    aluno = repositorio.adicionar(Aluno(**dados.model_dump()))
    db.commit()
    return aluno


def atualizar_aluno(db: Session, aluno_id: int, dados: AlunoAtualizacao) -> Aluno:
    repositorio = AlunoRepositorio(db)
    aluno = repositorio.obter_ou_falhar(aluno_id)
    alteracoes = mudancas(dados, aceitam_nulo={"cpf", "telefone", "data_nascimento"})
    if "turma_id" in alteracoes:
        referencia(TurmaRepositorio(db), alteracoes["turma_id"])
    if "cpf" in alteracoes:
        _cpf_livre(repositorio, alteracoes["cpf"], aluno.id)
    repositorio.atualizar(aluno, alteracoes)
    db.commit()
    return aluno


def inativar_aluno(db: Session, aluno_id: int) -> Aluno:
    repositorio = AlunoRepositorio(db)
    aluno = repositorio.obter_ou_falhar(aluno_id)
    repositorio.atualizar(aluno, {"status": "inativo"})
    db.commit()
    return aluno


def consultar_aluno(
    db: Session, *, aluno_id: int | None = None, matricula: str | None = None
) -> Aluno:
    """Consulta integrada (RF04): cadastro + disciplinas + notas + frequências."""
    aluno = AlunoRepositorio(db).obter_detalhado(id_=aluno_id, matricula=matricula)
    if aluno is None:
        chave = f"id {aluno_id}" if aluno_id is not None else f"matrícula {matricula}"
        raise RecursoNaoEncontrado(f"Aluno com {chave} não encontrado.")
    return aluno
