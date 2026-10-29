"""Models do serviço auth (ver docs/der.md).

Todos os models precisam ser importados aqui: o Alembic depende disso para gerar as migrações.
"""

from app.models.log_requisicao import LogRequisicao
from app.models.usuario import Usuario

__all__ = ["LogRequisicao", "Usuario"]
