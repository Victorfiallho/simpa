"""Perfis de acesso do analítico (D03): relatórios só para gestão; professor só vê o que é seu."""

import pytest

from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from tests.test_painel import cliente  # noqa: F401  (fixture com o acadêmico simulado)


def como(role: str, id_: int = 1) -> None:
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(id=id_, role=role)


@pytest.mark.parametrize("formato", ["csv", "xlsx", "pdf"])
def test_professor_nao_exporta_relatorios(cliente, formato):  # noqa: F811
    como("professor", 3)

    resposta = cliente.get("/relatorios/inscricoes", params={"formato": formato})

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "ACESSO_NEGADO"


@pytest.mark.parametrize("role", ["admin", "coordenador"])
def test_gestao_exporta_relatorios(cliente, role):  # noqa: F811
    como(role)

    assert cliente.get("/relatorios/inscricoes").status_code == 200


def test_professor_da_disciplina_ve_o_painel(cliente):  # noqa: F811
    como("professor", 3)

    assert cliente.get("/painel").json()["dados"]["total_alunos"] == 3


def test_professor_de_outra_disciplina_ve_painel_vazio(cliente):  # noqa: F811
    como("professor", 99)

    assert cliente.get("/painel").json()["dados"]["total_alunos"] == 0


def test_professor_nao_abre_indicadores_de_disciplina_alheia(cliente):  # noqa: F811
    como("professor", 99)

    resposta = cliente.get("/indicadores/disciplinas/1")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "DISCIPLINA_FORA_DO_ESCOPO"
