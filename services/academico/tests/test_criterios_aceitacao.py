"""Critérios de aceitação do SRS (seção 6) que ainda não tinham teste com o próprio nome.

O nome de cada teste diz o requisito e o critério: `test_rf01_ca03_...` é o 3º critério do RF01.
Os demais critérios estão ligados aos seus testes em docs/rastreabilidade.md.
"""

from typing import get_args

import pytest

from app.main import app
from app.schemas.aluno import StatusAluno
from tests.conftest import PROFESSOR_VALIDO, criar

# ---------- RF01: cadastro de alunos ----------


def test_rf01_ca02_matricula_nao_pode_ser_trocada_na_atualizacao(cliente, turma, aluno):
    """A matrícula é fixada no cadastro: a atualização não a aceita, nem repetida nem nova."""
    resposta = cliente.patch(f"/alunos/{aluno['id']}", json={"matricula": "20260077"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["campo"] == "matricula"


def test_rf01_ca03_cpf_ja_cadastrado_e_rejeitado(cliente, turma, aluno):
    resposta = cliente.post(
        "/alunos",
        json={
            "matricula": "20260099",
            "nome_completo": "Outra Pessoa",
            "cpf": "529.982.247-25",  # o mesmo do aluno da fixture
            "email": "outra@exemplo.com",
            "curso": "Inteligência Artificial",
            "turma_id": turma["id"],
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CPF_DUPLICADO"


def test_rf01_ca03_cpf_de_outro_aluno_e_rejeitado_na_atualizacao(cliente, turma, aluno):
    outro = criar(
        cliente,
        "/alunos",
        {
            "matricula": "20260098",
            "nome_completo": "Bruno Costa",
            "email": "bruno@exemplo.com",
            "curso": "Inteligência Artificial",
            "turma_id": turma["id"],
        },
    )

    resposta = cliente.patch(f"/alunos/{outro['id']}", json={"cpf": "529.982.247-25"})

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CPF_DUPLICADO"


def test_rf01_ca04_atualiza_os_dados_do_aluno(cliente, aluno):
    resposta = cliente.patch(f"/alunos/{aluno['id']}", json={"nome_completo": "Ana Beatriz Souza"})

    assert resposta.status_code == 200
    assert cliente.get(f"/alunos/{aluno['id']}").json()["dados"]["nome_completo"] == (
        "Ana Beatriz Souza"
    )


@pytest.mark.parametrize("situacao", get_args(StatusAluno))
def test_rf01_ca04_status_do_aluno_aceita_cada_valor_previsto(cliente, aluno, situacao):
    resposta = cliente.patch(f"/alunos/{aluno['id']}", json={"status": situacao})

    assert resposta.status_code == 200
    assert resposta.json()["dados"]["status"] == situacao


def test_rf01_ca04_status_fora_da_lista_e_rejeitado(cliente, aluno):
    resposta = cliente.patch(f"/alunos/{aluno['id']}", json={"status": "suspenso"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["campo"] == "status"


# ---------- RF02: turmas e disciplinas ----------


def test_rf02_ca02_codigo_de_disciplina_ja_existente_e_rejeitado(cliente, turma, disciplina):
    resposta = cliente.post(
        "/disciplinas",
        json={
            "codigo": disciplina["codigo"],
            "nome": "Outra disciplina",
            "carga_horaria": 40,
            "periodo_letivo": "2026.2",
            "turma_id": turma["id"],
            "professor_id": PROFESSOR_VALIDO,
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CODIGO_DUPLICADO"


@pytest.mark.parametrize("rota", ["turmas", "disciplinas"])
def test_rf02_ca04_atualiza_e_inativa_turma_e_disciplina(cliente, turma, disciplina, rota):
    registro = turma if rota == "turmas" else disciplina

    atualizada = cliente.patch(f"/{rota}/{registro['id']}", json={"nome": "Nome revisto"})
    inativada = cliente.delete(f"/{rota}/{registro['id']}")

    assert atualizada.status_code == 200
    assert atualizada.json()["dados"]["nome"] == "Nome revisto"
    assert inativada.status_code == 200
    # Exclusão lógica: o cadastro continua consultável, agora inativo.
    consulta = cliente.get(f"/{rota}/{registro['id']}").json()["dados"]
    assert consulta["status"] == "inativa"


# ---------- RF03: avaliações e frequência ----------


@pytest.mark.parametrize("peso", ["0", "-1.00"])
def test_rf03_ca02_peso_menor_ou_igual_a_zero_e_rejeitado(cliente, inscricao, peso, eventos):
    eventos.clear()  # o evento da criação da inscrição não interessa aqui

    resposta = cliente.post(
        "/avaliacoes",
        json={
            "inscricao_id": inscricao["id"],
            "tipo_avaliacao": "prova",
            "periodo_avaliacao": "N1",
            "nota": "7.00",
            "peso": peso,
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["campo"] == "peso"
    assert eventos == []  # nada persistido nem publicado (RF10)


# ---------- RF08: API REST padronizada ----------

PAGINACAO = {"pagina", "limite", "ordenar_por", "ordem"}


def _listagens() -> list[tuple[str, set[str]]]:
    """Rotas GET que devolvem lista paginada, com os parâmetros de query de cada uma."""
    esquema = app.openapi()
    rotas = []
    for caminho, metodos in esquema["paths"].items():
        get = metodos.get("get")
        if not get or "{" in caminho or caminho.startswith("/internal"):
            continue
        resposta = get["responses"]["200"]["content"]["application/json"]["schema"]
        if "RespostaPaginada" not in resposta.get("$ref", ""):
            continue
        parametros = {p["name"] for p in get.get("parameters", []) if p["in"] == "query"}
        rotas.append((caminho, parametros))
    return rotas


def test_rf08_ca02_existem_listagens_para_conferir():
    assert {c for c, _ in _listagens()} >= {"/turmas", "/disciplinas", "/alunos", "/inscricoes"}


@pytest.mark.parametrize(("caminho", "parametros"), _listagens())
def test_rf08_ca02_toda_listagem_aceita_paginacao_ordenacao_e_filtro(caminho, parametros):
    assert parametros >= PAGINACAO, f"{caminho} sem paginação ou ordenação"
    assert parametros - PAGINACAO, f"{caminho} sem nenhum filtro"


@pytest.mark.parametrize("caminho", [c for c, _ in _listagens()])
def test_rf08_ca02_listagem_responde_com_paginacao_e_ordem_pedidas(cliente, inscricao, caminho):
    resposta = cliente.get(
        caminho, params={"pagina": 1, "limite": 1, "ordenar_por": "id", "ordem": "desc"}
    )

    corpo = resposta.json()
    assert resposta.status_code == 200, corpo
    assert (corpo["pagina"], corpo["limite"]) == (1, 1)
    assert len(corpo["dados"]) <= 1
