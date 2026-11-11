"""RNF14: um erro inesperado responde 500 no formato padrão, sem stack trace nem detalhe interno.

Uma rota temporária lança uma exceção que nenhum tratador específico conhece. O detalhe
(mensagem e traceback) deve ficar só no log do serviço.
"""

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROTA = "/__teste_rnf14_erro_inesperado"
DETALHE_SECRETO = "detalhe-interno-que-nao-pode-vazar"


@pytest.fixture
def cliente_com_rota_quebrada():
    def quebra():
        raise RuntimeError(DETALHE_SECRETO)

    app.add_api_route(ROTA, quebra, methods=["GET"], include_in_schema=False)
    rota = app.router.routes[-1]
    try:
        # Sem isso o TestClient relança a exceção no teste em vez de devolver a resposta 500.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.router.routes.remove(rota)


def test_rnf14_erro_inesperado_responde_500_padronizado(cliente_com_rota_quebrada):
    resposta = cliente_com_rota_quebrada.get(ROTA)

    assert resposta.status_code == 500
    corpo = resposta.json()
    assert corpo["status"] == "erro"
    assert corpo["erro"]["codigo"] == "ERRO_INTERNO"
    assert corpo["mensagem"] == "Erro interno. Tente novamente."


def test_rnf14_resposta_500_nao_expoe_stack_trace_nem_detalhe(cliente_com_rota_quebrada):
    texto = cliente_com_rota_quebrada.get(ROTA).text

    for proibido in (DETALHE_SECRETO, "Traceback", "RuntimeError", 'File "', ".py"):
        assert proibido not in texto


def test_rnf14_detalhe_do_erro_fica_no_log(cliente_com_rota_quebrada, caplog):
    with caplog.at_level(logging.ERROR):
        cliente_com_rota_quebrada.get(ROTA)

    registros = [r for r in caplog.records if r.exc_info]
    assert registros, "o erro inesperado deveria ser registrado com o traceback"
    assert any(DETALHE_SECRETO in str(r.exc_info[1]) for r in registros)


def test_rnf14_resposta_500_devolve_o_request_id(cliente_com_rota_quebrada):
    """Quem recebe o erro consegue achar a requisição no log pelo X-Request-ID (RNF16)."""
    resposta = cliente_com_rota_quebrada.get(ROTA, headers={"X-Request-ID": "rnf14abc"})

    assert resposta.headers["X-Request-ID"] == "rnf14abc"


def test_rnf14_erro_inesperado_entra_na_auditoria_com_status_500(
    cliente_com_rota_quebrada, auditoria_enviada
):
    cliente_com_rota_quebrada.get(ROTA, headers={"X-Request-ID": "rnf14abc"})

    assert [(r["status_http"], r["correlation_id"]) for r in auditoria_enviada] == [
        (500, "rnf14abc")
    ]
