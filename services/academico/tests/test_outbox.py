"""Outbox: o evento nasce na mesma transação da alteração (D14)."""

import json
import uuid
from datetime import datetime

import pytest

from app.services import lancamentos
from tests.test_lancamentos import nota


def test_evento_tem_envelope_com_id_instante_e_dados(cliente, inscricao, eventos):
    eventos.clear()
    nota(cliente, inscricao)

    (linha,) = eventos.linhas()
    envelope = json.loads(linha.corpo)

    assert uuid.UUID(envelope["event_id"]).version == 4
    assert linha.id == envelope["event_id"]
    assert envelope["evento"] == linha.chave == "avaliacao.alterada"
    assert envelope["dados"] == {"inscricao_id": inscricao["id"]}
    assert datetime.fromisoformat(envelope["ocorrido_em"]).tzinfo is not None
    assert "request_id" in envelope
    assert linha.enviado_em is None and linha.tentativas == 0


def test_cada_evento_tem_um_id_proprio(cliente, inscricao, eventos):
    avaliacao = nota(cliente, inscricao).json()["dados"]
    cliente.patch(f"/avaliacoes/{avaliacao['id']}", json={"nota": "9.00"})

    ids = [linha.id for linha in eventos.linhas()]

    assert len(ids) == 3 and len(set(ids)) == 3


def test_se_a_transacao_falha_nem_a_alteracao_nem_o_evento_ficam(
    cliente, inscricao, eventos, monkeypatch
):
    """O evento é registrado antes do commit: se algo falha ali, os dois são desfeitos juntos."""
    eventos.clear()
    registrar_original = lancamentos.registrar_evento

    def registra_e_falha(db, chave, dados):
        registrar_original(db, chave, dados)
        raise RuntimeError("falha antes do commit")

    monkeypatch.setattr(lancamentos, "registrar_evento", registra_e_falha)

    with pytest.raises(RuntimeError):
        nota(cliente, inscricao)

    assert cliente.get("/avaliacoes").json()["total_registros"] == 0
    assert eventos.linhas() == []
