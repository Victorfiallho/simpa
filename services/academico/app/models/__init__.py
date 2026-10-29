"""Models do serviço acadêmico (ver docs/der.md).

Todos os models precisam ser importados aqui: o Alembic depende disso para gerar as migrações.
"""

from app.models.aluno import Aluno
from app.models.avaliacao import Avaliacao
from app.models.disciplina import Disciplina
from app.models.frequencia import Frequencia
from app.models.inscricao import Inscricao
from app.models.turma import Turma

__all__ = ["Aluno", "Avaliacao", "Disciplina", "Frequencia", "Inscricao", "Turma"]
