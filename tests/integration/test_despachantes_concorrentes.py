"""Despachantes concorrentes no PostgreSQL real (etapa 4.5 do plano de qualidade).

O SQLite dos testes unitários ignora `FOR UPDATE SKIP LOCKED`; só o PostgreSQL prova que dois
despachantes não pegam o mesmo evento. Para o teste ser determinístico, o despachante do ambiente é
parado enquanto os dois "despachantes" do teste abrem as transações, e religado no `finally`.
"""

from __future__ import annotations

import pytest

from tests.integration import suporte

SCRIPT = """
from datetime import UTC, datetime
from sqlalchemy import select
from app.core.database import get_sessionmaker
from app.events.outbox import registrar_evento
from app.models import EventoOutbox

fabrica = get_sessionmaker()
with fabrica() as db:  # dois eventos pendentes (inscrição inexistente: o worker os ignora)
    for _ in range(2):
        registrar_evento(db, "inscricao.alterada", {"inscricao_id": 999999})
    db.commit()


def proximo(db):
    agora = datetime.now(UTC)
    return db.scalars(
        select(EventoOutbox)
        .where(EventoOutbox.enviado_em.is_(None), EventoOutbox.proxima_tentativa_em <= agora)
        .order_by(EventoOutbox.criado_em, EventoOutbox.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()


a, b, c = fabrica(), fabrica(), fabrica()
ea, eb, ec = proximo(a), proximo(b), proximo(c)
print(ea.id, eb.id if eb else None, ec.id if ec else None)
a.rollback(); b.rollback(); c.rollback()
"""


@pytest.mark.interrupcao
def test_dois_despachantes_nao_pegam_o_mesmo_evento():
    try:
        suporte.compose("stop", "academico-despachante", timeout=60)
        saida = suporte.compose("exec", "-T", "academico", "python", "-c", SCRIPT).stdout.split()
    finally:
        suporte.compose(
            "up", "-d", "--no-build", "--wait", "--wait-timeout", "90", "academico-despachante",
            timeout=120,
        )  # fmt: skip

    primeiro, segundo, terceiro = saida
    assert primeiro != "None" and segundo != "None", "cada despachante deveria ter pegado um evento"
    assert primeiro != segundo, "os dois despachantes pegaram o mesmo evento"
    assert terceiro == "None", "com as duas linhas travadas, o terceiro não deveria achar nada"
