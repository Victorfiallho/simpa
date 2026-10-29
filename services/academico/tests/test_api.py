"""Testes da API do acadêmico: saúde e validação do token emitido pelo auth."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.core import seguranca
from app.main import app

CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OUTRA_CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _JwksFalso:
    """Substitui o PyJWKClient para não depender do serviço auth no teste."""

    def get_signing_key_from_jwt(self, _token):
        jwk = RSAAlgorithm.to_jwk(CHAVE.public_key(), as_dict=True)
        return jwt.PyJWK.from_dict({**jwk, "alg": "RS256"})


@pytest.fixture(autouse=True)
def jwks_falso(monkeypatch):
    monkeypatch.setattr(seguranca, "_cliente_jwks", _JwksFalso)


def _token(chave=CHAVE, **alteracoes) -> HTTPAuthorizationCredentials:
    agora = datetime.now(UTC)
    payload = {
        "sub": "7",
        "role": "professor",
        "iss": "simpa-auth",
        "exp": agora + timedelta(minutes=5),
    } | alteracoes
    token = jwt.encode(payload, chave, algorithm="RS256")
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_health():
    resposta = TestClient(app).get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "academico"}


def test_token_valido_devolve_o_usuario():
    usuario = seguranca.usuario_atual(_token())

    assert usuario == seguranca.UsuarioAtual(id=7, role="professor")


@pytest.mark.parametrize(
    "credenciais",
    [
        None,
        _token(chave=OUTRA_CHAVE),
        _token(exp=datetime.now(UTC) - timedelta(minutes=1)),
        _token(iss="outro-emissor"),
        _token(role="aluno"),
    ],
    ids=["sem-token", "assinatura-errada", "expirado", "emissor-errado", "role-invalida"],
)
def test_token_invalido_responde_401(credenciais):
    with pytest.raises(HTTPException) as erro:
        seguranca.usuario_atual(credenciais)

    assert erro.value.status_code == 401
