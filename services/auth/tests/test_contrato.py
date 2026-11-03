"""Contrato da API do auth (RF08, RF09, RNF14): envelope, erros padronizados e OpenAPI honesto."""

from datetime import UTC, datetime

import pytest

from app.core import seguranca
from app.main import app
from app.models import LogRequisicao
from tests.test_usuarios import SENHA, cliente, entrar, sessoes  # noqa: F401

ENVELOPE = {"status", "mensagem", "dados", "erro"}
LISTAGEM = ENVELOPE | {"pagina", "limite", "total_registros"}
OPERACOES = {"get", "post", "put", "patch", "delete"}
ABERTAS = {"/health", "/.well-known/jwks.json"}


def operacoes():
    for caminho, itens in app.openapi()["paths"].items():
        for metodo, operacao in itens.items():
            if metodo in OPERACOES:
                yield caminho, metodo, operacao


def cab(role="admin", usuario_id=1) -> dict:
    return {"Authorization": f"Bearer {seguranca.criar_token(usuario_id, role, 'Fulano')}"}


# ---------- OpenAPI ----------


def test_toda_rota_documenta_400_e_500():
    faltando = [
        f"{m.upper()} {c}" for c, m, o in operacoes() if not {"400", "500"} <= set(o["responses"])
    ]

    assert faltando == []


def test_rotas_protegidas_documentam_401_e_403():
    faltando = [
        f"{m.upper()} {c}"
        for c, m, o in operacoes()
        if c not in ABERTAS | {"/login"} and not {"401", "403"} <= set(o["responses"])
    ]

    assert faltando == []


def test_login_documenta_401_422_e_429_mas_nao_403():
    respostas = app.openapi()["paths"]["/login"]["post"]["responses"]

    assert {"200", "401", "422", "429"} <= set(respostas)
    assert "403" not in respostas


def test_erros_apontam_para_o_envelope_padrao():
    esquema = app.openapi()
    erro = esquema["paths"]["/login"]["post"]["responses"]["401"]

    assert erro["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErroPadrao"
    }
    assert set(esquema["components"]["schemas"]["ErroPadrao"]["properties"]) == ENVELOPE


# ---------- Respostas reais ----------


def test_login_segue_o_envelope(cliente):  # noqa: F811
    resposta = entrar(cliente, "admin@simpa.dev", SENHA)

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert set(corpo) == ENVELOPE
    assert {"access_token", "expira_em_minutos", "usuario"} <= set(corpo["dados"])
    assert {"id", "nome_usuario", "role"} <= set(corpo["dados"]["usuario"])


def test_login_errado_nao_diz_qual_campo_errou(cliente):  # noqa: F811
    certo = entrar(cliente, "admin@simpa.dev", "errada").json()
    inexistente = entrar(cliente, "ninguem@simpa.dev", SENHA).json()

    assert certo["erro"] == inexistente["erro"]
    assert certo["erro"]["codigo"] == "NAO_AUTENTICADO"
    assert set(certo) == ENVELOPE


def test_auditoria_traz_paginacao(cliente, sessoes):  # noqa: F811
    with sessoes() as db:
        db.add(
            LogRequisicao(
                correlation_id="c1",
                usuario_id=1,
                rota="/turmas",
                metodo_http="GET",
                status_http=200,
                ip_origem="10.0.0.1",
                tempo_resposta_ms=5,
                timestamp=datetime.now(UTC),
            )
        )
        db.commit()

    corpo = cliente.get("/auditoria", headers=cab()).json()

    assert set(corpo) == LISTAGEM
    assert set(corpo["dados"][0]) >= {"correlation_id", "rota", "status_http", "timestamp"}


@pytest.mark.parametrize("rota", ["/auditoria", "/me"])
def test_sem_token_responde_401_no_envelope(cliente, rota):  # noqa: F811
    resposta = cliente.get(rota)

    assert resposta.status_code == 401
    assert resposta.json()["erro"]["codigo"] == "NAO_AUTENTICADO"
    assert set(resposta.json()) == ENVELOPE


def test_professor_na_auditoria_responde_403_no_envelope(cliente):  # noqa: F811
    resposta = cliente.get("/auditoria", headers=cab("professor", 3))

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "ACESSO_NEGADO"
    assert set(resposta.json()) == ENVELOPE
