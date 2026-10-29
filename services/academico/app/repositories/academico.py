"""Repositórios de cada entidade do serviço acadêmico."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Aluno, Avaliacao, Disciplina, Frequencia, Inscricao, Turma
from app.repositories.base import Repositorio


class TurmaRepositorio(Repositorio[Turma]):
    modelo = Turma
    nome = "Turma"
    campos_ordenaveis = frozenset({"id", "nome", "periodo_letivo", "codigo"})


class DisciplinaRepositorio(Repositorio[Disciplina]):
    modelo = Disciplina
    nome = "Disciplina"
    campos_ordenaveis = frozenset({"id", "nome", "periodo_letivo", "codigo"})


class AlunoRepositorio(Repositorio[Aluno]):
    modelo = Aluno
    nome = "Aluno"
    campos_ordenaveis = frozenset({"id", "nome_completo", "matricula"})

    def obter_detalhado(
        self, *, id_: int | None = None, matricula: str | None = None
    ) -> Aluno | None:
        """Aluno com inscrições, disciplinas, notas e frequências, em poucas consultas (RF04)."""
        consulta = select(Aluno).options(
            selectinload(Aluno.inscricoes).selectinload(Inscricao.avaliacoes),
            selectinload(Aluno.inscricoes).selectinload(Inscricao.frequencias),
        )
        consulta = (
            consulta.where(Aluno.id == id_)
            if id_ is not None
            else consulta.where(Aluno.matricula == matricula)
        )
        return self.db.scalar(consulta)


class InscricaoRepositorio(Repositorio[Inscricao]):
    modelo = Inscricao
    nome = "Inscrição"
    campos_ordenaveis = frozenset({"id", "criado_em"})

    def obter_detalhada(self, id_: int) -> Inscricao | None:
        consulta = (
            select(Inscricao)
            .options(selectinload(Inscricao.avaliacoes), selectinload(Inscricao.frequencias))
            .where(Inscricao.id == id_)
        )
        return self.db.scalar(consulta)


class AvaliacaoRepositorio(Repositorio[Avaliacao]):
    modelo = Avaliacao
    nome = "Avaliação"
    campos_ordenaveis = frozenset({"id", "periodo_avaliacao", "nota", "atualizado_em"})


class FrequenciaRepositorio(Repositorio[Frequencia]):
    modelo = Frequencia
    nome = "Frequência"
    campos_ordenaveis = frozenset({"id", "periodo_avaliacao"})
