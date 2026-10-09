"""Engine, sessão e Base declarativa do SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe base de todos os models. O Alembic lê Base.metadata."""


engine = create_engine(get_settings().database_url)


@event.listens_for(engine, "connect")
def _ativar_fk_sqlite(dbapi_conn, _record) -> None:
    # O SQLite ignora FOREIGN KEY por padrão; sem isso o ON DELETE RESTRICT não vale.
    if engine.dialect.name == "sqlite":
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e sempre fecha."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
