"""Models do serviço analítico (ver docs/der.md).

Todos os models precisam ser importados aqui: o Alembic depende disso para gerar as migrações.
"""

from app.models.alerta import Acompanhamento, AtendimentoAlerta
from app.models.resultado_risco import ResultadoRisco

__all__ = ["Acompanhamento", "AtendimentoAlerta", "ResultadoRisco"]
