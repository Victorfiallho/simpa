"""Testes da API do auth: saúde, correlation id e tokens validáveis pelo JWKS."""

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import seguranca
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAVES_DIR", str(tmp_path))
    get_settings.cache_clear()
    seguranca.chave_privada.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()
    seguranca.chave_privada.cache_clear()


def test_health(cliente):
    resposta = cliente.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "auth"}


def test_devolve_o_request_id_recebido_do_gateway(cliente):
    resposta = cliente.get("/health", headers={"X-Request-ID": "abc123"})

    assert resposta.headers["X-Request-ID"] == "abc123"


def test_token_emitido_e_validado_com_a_chave_publica_do_jwks(cliente):
    token = seguranca.criar_token(usuario_id=7, role="professor")

    chave = cliente.get("/.well-known/jwks.json").json()["keys"][0]
    chave_publica = jwt.PyJWK(chave).key
    dados = jwt.decode(token, chave_publica, algorithms=["RS256"], issuer="simpa-auth")

    assert dados["sub"] == "7"
    assert dados["role"] == "professor"


def test_chave_privada_e_reaproveitada_entre_reinicios(cliente, tmp_path):
    primeira = seguranca.jwks()
    seguranca.chave_privada.cache_clear()

    assert seguranca.jwks() == primeira
    assert (tmp_path / "privada.pem").exists()
