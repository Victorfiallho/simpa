"""Entradas hostis no auth (RNF04): SQL no login e na auditoria, HTML no perfil, repetidos."""

from datetime import UTC, datetime

import pytest

from app.core import seguranca
from app.models import LogRequisicao
from tests.test_usuarios import SENHA, cliente, entrar, sessoes  # noqa: F401

SQL = ["' OR '1'='1", "'; DROP TABLE usuario; --", '" OR ""="', "admin@simpa.dev'--"]


def cab(role="admin", usuario_id=1) -> dict:
    return {"Authorization": f"Bearer {seguranca.criar_token(usuario_id, role, 'Fulano')}"}


def codigo(resposta) -> str:
    return resposta.json()["erro"]["codigo"]


# ---------- Login ----------


@pytest.mark.parametrize("carga", SQL)
def test_login_com_sql_no_email_e_recusado(cliente, carga):  # noqa: F811
    resposta = entrar(cliente, carga, SENHA)

    assert resposta.status_code in (401, 422)
    assert "access_token" not in resposta.text


@pytest.mark.parametrize("carga", SQL)
def test_login_com_sql_na_senha_nao_entra(cliente, carga):  # noqa: F811
    resposta = entrar(cliente, "admin@simpa.dev", carga)

    assert resposta.status_code == 401
    assert "access_token" not in resposta.text
    # O usuário continua existindo e entrando com a senha certa.
    assert entrar(cliente, "admin@simpa.dev", SENHA).status_code == 200


# ---------- Auditoria ----------


@pytest.fixture
def com_registros(cliente, sessoes):  # noqa: F811
    with sessoes() as db:
        for i, rota in enumerate(["/turmas", "/alunos", "/login"]):
            db.add(
                LogRequisicao(
                    correlation_id=f"c{i}",
                    usuario_id=7,
                    rota=rota,
                    metodo_http="GET",
                    status_http=200,
                    ip_origem="10.0.0.1",
                    tempo_resposta_ms=5,
                    timestamp=datetime.now(UTC),
                )
            )
        db.commit()
    return cliente


@pytest.mark.parametrize("carga", SQL)
def test_busca_da_auditoria_com_sql_nao_acha_nada(com_registros, carga):
    resposta = com_registros.get("/auditoria", params={"busca": carga}, headers=cab())

    assert resposta.status_code == 200
    assert resposta.json()["total_registros"] == 0
    assert com_registros.get("/auditoria", headers=cab()).json()["total_registros"] == 3


@pytest.mark.parametrize("carga", SQL)
def test_ordenar_por_da_auditoria_so_aceita_campos_da_lista(com_registros, carga):
    resposta = com_registros.get("/auditoria", params={"ordenar_por": carga}, headers=cab())

    assert resposta.status_code == 422
    assert codigo(resposta) == "ORDENACAO_INVALIDA"


@pytest.mark.parametrize("curinga", ["%%", "_a", "%s%", "a\\"])
def test_curingas_da_busca_valem_como_letras(com_registros, curinga):
    resposta = com_registros.get("/auditoria", params={"busca": curinga}, headers=cab())

    assert resposta.status_code == 200
    assert resposta.json()["total_registros"] == 0


@pytest.mark.parametrize("consulta", ["limite=5&limite=500", "metodo_http=GET&metodo_http=POST"])
def test_auditoria_recusa_parametro_repetido(com_registros, consulta):
    resposta = com_registros.get(f"/auditoria?{consulta}", headers=cab())

    assert resposta.status_code == 400
    assert codigo(resposta) == "PARAMETRO_REPETIDO"


def test_parametro_repetido_vale_ate_sem_login(cliente):  # noqa: F811
    assert cliente.get("/auditoria?limite=1&limite=2").status_code == 400


# ---------- Perfil ----------


@pytest.mark.parametrize(
    "campo", ["nome_completo", "cargo", "rua", "cidade", "emergencia_nome", "complemento"]
)
def test_perfil_recusa_html_em_texto_livre(cliente, campo):  # noqa: F811
    resposta = cliente.patch(
        "/me", json={campo: "<script>alert(1)</script>"}, headers=cab("professor", 3)
    )

    assert resposta.status_code == 422
    assert codigo(resposta) == "VALIDACAO"


def test_perfil_aceita_apostrofo_e_e_comercial(cliente):  # noqa: F811
    resposta = cliente.patch(
        "/me", json={"nome_completo": "Ana D'Ávila & Silva"}, headers=cab("professor", 3)
    )

    assert resposta.status_code == 200
    assert resposta.json()["dados"]["nome_completo"] == "Ana D'Ávila & Silva"


def test_cpf_do_perfil_so_sai_mascarado(cliente):  # noqa: F811
    cliente.patch("/me", json={"cpf": "529.982.247-25"}, headers=cab("professor", 3))

    resposta = cliente.get("/me", headers=cab("professor", 3))

    assert "52998224725" not in resposta.text
    assert "529.982.247-25" not in resposta.text
    assert "***.982.247-**" in resposta.text
