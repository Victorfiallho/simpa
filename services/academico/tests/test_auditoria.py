"""Auditoria das requisições (RF12, RNF16): o que é enviado e, principalmente, o que não é."""

from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.core import seguranca
from app.core.auditoria import CAMPOS, mascarar
from app.main import app

CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _JwksFalso:
    def get_signing_key_from_jwt(self, _token):
        jwk = RSAAlgorithm.to_jwk(CHAVE.public_key(), as_dict=True)
        return jwt.PyJWK.from_dict({**jwk, "alg": "RS256"})


def test_registra_a_requisicao(cliente, auditoria_enviada):
    cliente.get("/turmas", headers={"X-Request-ID": "abc123", "X-Real-IP": "10.0.0.7"})

    registro = auditoria_enviada[-1]
    assert registro["correlation_id"] == "abc123"
    assert registro["rota"] == "/turmas"
    assert registro["metodo_http"] == "GET"
    assert registro["status_http"] == 200
    assert registro["ip_origem"] == "10.0.0.7"
    assert registro["tempo_resposta_ms"] >= 0


def test_so_envia_os_campos_previstos(cliente, auditoria_enviada):
    cliente.get(
        "/turmas?busca=segredo",
        headers={"Authorization": "Bearer token-secreto", "Cookie": "sessao=x"},
    )

    registro = auditoria_enviada[-1]
    assert set(registro) == set(CAMPOS)
    texto = str(registro)
    assert "token-secreto" not in texto
    assert "segredo" not in texto  # a query string fica de fora
    assert "sessao" not in texto


def test_nao_registra_health_nem_rotas_internas(cliente, auditoria_enviada):
    cliente.get("/health")
    cliente.get("/internal/inscricoes")

    assert auditoria_enviada == []


def test_cpf_no_caminho_e_mascarado(cliente, auditoria_enviada):
    cliente.get("/alunos/529.982.247-25")
    cliente.get("/alunos/52998224725")

    assert [r["rota"] for r in auditoria_enviada] == [
        "/alunos/***.***.***-**",
        "/alunos/***.***.***-**",
    ]


def test_mascarar_nao_mexe_em_numeros_que_nao_sao_cpf():
    assert mascarar("/alunos/20260001") == "/alunos/20260001"
    assert mascarar("/x/123456789012345") == "/x/123456789012345"


def test_usuario_do_token_vai_para_o_registro(cliente, monkeypatch, auditoria_enviada):
    app.dependency_overrides.pop(seguranca.usuario_atual)
    monkeypatch.setattr(seguranca, "_cliente_jwks", _JwksFalso)
    token = jwt.encode(
        {
            "sub": "42",
            "role": "professor",
            "iss": "simpa-auth",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        CHAVE,
        algorithm="RS256",
    )

    resposta = cliente.get("/turmas", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200
    assert auditoria_enviada[-1]["usuario_id"] == 42


def test_requisicao_sem_token_fica_sem_usuario(cliente, auditoria_enviada):
    app.dependency_overrides.pop(seguranca.usuario_atual)
    resposta = cliente.get("/turmas")

    assert resposta.status_code == 401
    assert auditoria_enviada[-1]["usuario_id"] is None
    assert auditoria_enviada[-1]["status_http"] == 401
