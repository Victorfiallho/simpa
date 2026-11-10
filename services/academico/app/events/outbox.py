"""Registro de eventos na outbox, dentro da transação da alteração (D14).

Chame ANTES do `commit()`: o evento e a alteração são gravados juntos. Se a transação for
desfeita, o evento some com ela, e nada é anunciado sem ter acontecido.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logs import request_id_atual
from app.models import EventoOutbox


def registrar_evento(db: Session, chave: str, dados: dict[str, Any]) -> EventoOutbox:
    """Acrescenta o evento à sessão (sem commit). O envelope já leva o momento da alteração."""
    evento_id = str(uuid.uuid4())
    envelope = {
        "evento": chave,
        "event_id": evento_id,
        "request_id": request_id_atual.get(),
        "ocorrido_em": datetime.now(UTC).isoformat(),
        "dados": dados,
    }
    evento = EventoOutbox(id=evento_id, chave=chave, corpo=json.dumps(envelope))
    db.add(evento)
    return evento
