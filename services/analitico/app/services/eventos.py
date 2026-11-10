"""Controle de eventos já processados (idempotência, D14)."""

from sqlalchemy.exc import IntegrityError

from app.core.database import get_sessionmaker
from app.models import EventoProcessado


def ja_processado(event_id: str) -> bool:
    with get_sessionmaker()() as db:
        return db.get(EventoProcessado, event_id) is not None


def marcar_processado(event_id: str) -> None:
    """Anota o evento. Se outro processo anotou antes, tudo bem: o efeito é o mesmo."""
    with get_sessionmaker()() as db:
        db.add(EventoProcessado(event_id=event_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
