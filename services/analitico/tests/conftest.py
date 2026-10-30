import pytest

from app.core import auditoria


@pytest.fixture(autouse=True)
def auditoria_enviada(monkeypatch):
    """Registros de auditoria que iriam para o RabbitMQ; nenhum teste abre conexão."""
    enviados: list[dict] = []
    monkeypatch.setattr(auditoria, "enviar", enviados.append)
    return enviados
