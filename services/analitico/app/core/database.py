"""Engine, sessão e Base declarativa do SQLAlchemy.

O engine é criado sob demanda (e não na importação do módulo), para que importar um
model nos testes ou no Alembic não exija o .env completo.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe base de todos os models. O Alembic lê Base.metadata."""


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
