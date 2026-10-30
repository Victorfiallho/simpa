"""Auditoria no analítico (RF12, RNF16): registro por requisição, sem dados pessoais."""

from app.core.auditoria import CAMPOS
from tests.test_painel import cliente  # noqa: F401  (acadêmico simulado)


def test_painel_e_registrado_sem_query_string(cliente, auditoria_enviada):  # noqa: F811
    cliente.get("/painel?periodo_letivo=2026.2", headers={"X-Request-ID": "xyz"})

    registro = auditoria_enviada[-1]
    assert set(registro) == set(CAMPOS)
    assert registro["correlation_id"] == "xyz"
    assert registro["rota"] == "/painel"
    assert registro["status_http"] == 200
    assert "2026.2" not in str(registro)


def test_health_nao_e_registrado(cliente, auditoria_enviada):  # noqa: F811
    cliente.get("/health")

    assert auditoria_enviada == []
