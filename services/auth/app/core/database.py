"""Engine, sessão e Base declarativa do SQLAlchemy.

O engine é criado sob demanda (e não na importação do módulo), para que importar um
model nos testes ou no Alembic não exija o .env completo.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Nomes previsíveis para índices e constraints; o Alembic depende disso para alterá-los depois.
CONVENCAO_DE_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Classe base de todos os models. O Alembic lê Base.metadata."""

    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


@lru_cache
def get_engine() -> Engine:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)

    if engine.dialect.name == "sqlite":
        # O SQLite (usado só em testes) ignora FOREIGN KEY por padrão.
        @event.listens_for(engine, "connect")
        def _ativar_fk_sqlite(dbapi_conn, _record) -> None:
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Dependência do FastAPI: uma sessão por requisição.

    Regra de transação: os repositórios só fazem add/flush. O service chama
    db.commit() uma única vez, ao final do caso de uso. Se algo falhar antes,
    nada é gravado.
    """
    db = get_sessionmaker()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
