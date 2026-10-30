"""GET /auditoria (RF12): quem pode ler a trilha e como filtrar."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core import seguranca
from app.models import LogRequisicao
from tests.test_usuarios import cliente, sessoes  # noqa: F401


def cabecalho(role: str, id_: int = 1) -> dict:
    token = seguranca.criar_token(usuario_id=id_, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def com_registros(cliente, sessoes):  # noqa: F811
    agora = datetime.now(UTC)
    linhas = [
        ("a1", 7, "/turmas", "GET", 200, 0),
        ("a2", 7, "/alunos", "POST", 201, 1),
        ("a3", None, "/login", "POST", 401, 2),
        ("a4", 9, "/alunos/1", "GET", 404, 3),
        ("a5", 9, "/disciplinas", "GET", 500, 4),
    ]
    with sessoes() as db:
        for cid, uid, rota, metodo, status, minutos in linhas:
            db.add(
                LogRequisicao(
                    correlation_id=cid,
                    usuario_id=uid,
                    rota=rota,
                    metodo_http=metodo,
                    status_http=status,
                    ip_origem="10.0.0.1",
                    tempo_resposta_ms=5,
                    timestamp=agora - timedelta(minutes=10 - minutos),
                )
            )
        db.commit()
    return cliente


def listar(http, perfil="admin", **params):
    return http.get("/auditoria", params=params, headers=cabecalho(perfil))


def test_sem_token_e_401(com_registros):
    assert com_registros.get("/auditoria").status_code == 401


def test_professor_nao_le_a_auditoria(com_registros):
    resposta = listar(com_registros, "professor")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "ACESSO_NEGADO"


@pytest.mark.parametrize("perfil", ["admin", "coordenador"])
def test_admin_e_coordenador_leem(com_registros, perfil):
    resposta = listar(com_registros, perfil)

    assert resposta.status_code == 200
    assert resposta.json()["total_registros"] == 5


def test_mais_recentes_primeiro(com_registros):
    corpo = listar(com_registros, ordenar_por="timestamp", ordem="desc").json()

    assert [r["correlation_id"] for r in corpo["dados"]][:2] == ["a5", "a4"]


def test_pagina_os_resultados(com_registros):
    corpo = listar(com_registros, limite=2, pagina=3).json()

    assert (corpo["total_registros"], len(corpo["dados"])) == (5, 1)


@pytest.mark.parametrize(
    ("filtro", "esperado"),
    [
        ({"usuario_id": 7}, {"a1", "a2"}),
        ({"status_http": 404}, {"a4"}),
        ({"classe_status": 4}, {"a3", "a4"}),
        ({"classe_status": 2}, {"a1", "a2"}),
        ({"metodo_http": "post"}, {"a2", "a3"}),
        ({"busca": "alunos"}, {"a2", "a4"}),
        ({"busca": "a5"}, {"a5"}),
    ],
)
def test_filtros(com_registros, filtro, esperado):
    corpo = listar(com_registros, **filtro).json()

    assert {r["correlation_id"] for r in corpo["dados"]} == esperado


def test_filtro_por_periodo(com_registros):
    corte = (datetime.now(UTC) - timedelta(minutes=7, seconds=30)).isoformat()

    corpo = listar(com_registros, desde=corte).json()

    assert {r["correlation_id"] for r in corpo["dados"]} == {"a4", "a5"}


def test_ordenar_por_campo_invalido_e_422(com_registros):
    resposta = listar(com_registros, ordenar_por="ip_origem")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ORDENACAO_INVALIDA"


def test_resposta_so_traz_os_campos_previstos(com_registros):
    registro = listar(com_registros).json()["dados"][0]

    assert set(registro) == {
        "id",
        "correlation_id",
        "usuario_id",
        "rota",
        "metodo_http",
        "status_http",
        "ip_origem",
        "tempo_resposta_ms",
        "timestamp",
    }


def test_token_de_outra_chave_e_recusado(com_registros):
    falso = jwt.encode({"sub": "1", "role": "admin", "iss": "simpa-auth"}, "x" * 40, "HS256")

    resposta = com_registros.get("/auditoria", headers={"Authorization": f"Bearer {falso}"})

    assert resposta.status_code == 401
