"""GET /usuarios: a gestão lista usuários (por exemplo, professores) sem ver dados pessoais."""

import pytest

from app.core import seguranca
from app.models import Usuario
from tests.test_usuarios import cliente, sessoes  # noqa: F401


def cabecalho(role: str) -> dict:
    return {"Authorization": f"Bearer {seguranca.criar_token(usuario_id=1, role=role)}"}


@pytest.mark.parametrize("role", ["admin", "coordenador"])
def test_gestao_lista_professores(cliente, role):  # noqa: F811
    resposta = cliente.get("/usuarios", params={"role": "professor"}, headers=cabecalho(role))
    assert resposta.status_code == 200
    corpo = resposta.json()
    nomes = [u["nome_usuario"] for u in corpo["dados"]]
    assert len(nomes) >= 2
    assert nomes == sorted(nomes)
    assert {u["role"] for u in corpo["dados"]} == {"professor"}
    assert corpo["total_registros"] == len(nomes)


def test_resposta_nao_traz_email_nem_senha(cliente):  # noqa: F811
    corpo = cliente.get("/usuarios", headers=cabecalho("admin")).json()
    for usuario in corpo["dados"]:
        assert set(usuario) == {"id", "nome_usuario", "role", "ativo", "aluno_id"}


@pytest.mark.parametrize("role", ["professor", "aluno"])
def test_professor_e_aluno_nao_listam_usuarios(cliente, role):  # noqa: F811
    assert cliente.get("/usuarios", headers=cabecalho(role)).status_code == 403


def test_sem_token_e_recusado(cliente):  # noqa: F811
    assert cliente.get("/usuarios").status_code == 401


def test_pagina_e_filtro_de_ativo(cliente, sessoes):  # noqa: F811
    with sessoes() as db:
        primeiro = (
            db.query(Usuario).filter(Usuario.role == "professor").order_by(Usuario.id).first()
        )
        primeiro.ativo = False
        db.commit()
    ativos = cliente.get(
        "/usuarios", params={"role": "professor", "ativo": "true"}, headers=cabecalho("admin")
    ).json()
    assert primeiro.id not in [u["id"] for u in ativos["dados"]]
    pagina = cliente.get("/usuarios", params={"limite": 1}, headers=cabecalho("admin")).json()
    assert len(pagina["dados"]) == 1 and pagina["total_registros"] > 1


def test_perfil_invalido_e_rejeitado(cliente):  # noqa: F811
    resposta = cliente.get("/usuarios", params={"role": "hacker"}, headers=cabecalho("admin"))
    assert resposta.status_code == 422
