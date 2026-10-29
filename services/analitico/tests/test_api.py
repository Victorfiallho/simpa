"""Testes do analítico: saúde da API e processamento dos eventos pelo worker."""

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.events import consumidor
from app.main import app


class _CanalFalso:
    def __init__(self):
        self.acks: list[int] = []
        self.nacks: list[int] = []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        assert requeue is False
        self.nacks.append(delivery_tag)


def _metodo(tag=1):
    return SimpleNamespace(delivery_tag=tag, routing_key="avaliacao.alterada")


def test_health():
    resposta = TestClient(app).get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "analitico"}


def test_evento_valido_recalcula_e_confirma(monkeypatch):
    chamadas = []
    monkeypatch.setattr(consumidor, "recalcular_risco_da_inscricao", chamadas.append)
    canal = _CanalFalso()
    corpo = json.dumps({"evento": "avaliacao.alterada", "dados": {"inscricao_id": 42}})

    consumidor.processar(canal, _metodo(), None, corpo.encode())

    assert chamadas == [42]
    assert canal.acks == [1]
    assert canal.nacks == []


def test_evento_invalido_vai_para_a_fila_de_falhas():
    canal = _CanalFalso()

    consumidor.processar(canal, _metodo(), None, b"isto nao e json")

    assert canal.acks == []
    assert canal.nacks == [1]
