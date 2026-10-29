"""Turmas, disciplinas e alunos: validações, unicidade, D10 e formato das respostas."""

import pytest

from tests.conftest import criar


def test_resposta_tem_o_formato_padrao(cliente, turma):
    corpo = cliente.get(f"/turmas/{turma['id']}").json()

    assert corpo["status"] == "sucesso"
    assert corpo["erro"] is None
    assert corpo["dados"]["codigo"] == "IA2-N"


def test_listagem_paginada_e_ordenada(cliente, turma):
    for n in range(3):
        criar(
            cliente,
            "/turmas",
            {"nome": f"Turma {n}", "curso": "IA", "periodo_letivo": "2026.2", "turno": "matutino"},
        )

    corpo = cliente.get("/turmas", params={"limite": 2, "pagina": 2, "ordenar_por": "nome"}).json()

    assert corpo["total_registros"] == 4
    assert corpo["pagina"] == 2
    assert corpo["limite"] == 2
    # Ordem por nome: "IA 2º período", "Turma 0", "Turma 1", "Turma 2" → página 2 = 3º e 4º.
    assert [t["nome"] for t in corpo["dados"]] == ["Turma 1", "Turma 2"]


def test_ordenacao_por_campo_nao_permitido(cliente):
    resposta = cliente.get("/alunos", params={"ordenar_por": "cpf"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ORDENACAO_INVALIDA"


def test_validacao_informa_campo_regra_e_codigo(cliente):
    resposta = cliente.post("/turmas", json={"nome": "", "periodo_letivo": "2026/2"})

    erro = resposta.json()["erro"]
    assert resposta.status_code == 422
    assert erro["codigo"] == "VALIDACAO"
    campos = {c["campo"]: c for c in erro["campos"]}
    assert campos["curso"]["mensagem"] == "Campo obrigatório."
    assert campos["periodo_letivo"]["regra"] == "string_pattern_mismatch"
    assert "nome" in campos


def test_campo_desconhecido_e_recusado(cliente, turma):
    resposta = cliente.patch(f"/turmas/{turma['id']}", json={"senha": "x"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["regra"] == "extra_forbidden"


def test_codigo_de_turma_unico(cliente, turma):
    resposta = cliente.post(
        "/turmas",
        json={
            "codigo": "IA2-N",
            "nome": "Outra",
            "curso": "IA",
            "periodo_letivo": "2026.2",
            "turno": "noturno",
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "CODIGO_DUPLICADO"


def test_matricula_unica(cliente, aluno, turma):
    resposta = cliente.post(
        "/alunos",
        json={
            "matricula": aluno["matricula"],
            "nome_completo": "Outra Pessoa",
            "email": "outra@exemplo.com",
            "curso": "IA",
            "turma_id": turma["id"],
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "MATRICULA_DUPLICADA"


@pytest.mark.parametrize("cpf", ["123.456.789-00", "111.111.111-11", "1234"])
def test_cpf_invalido(cliente, turma, cpf):
    resposta = cliente.post(
        "/alunos",
        json={
            "matricula": "20260002",
            "nome_completo": "Bruno Costa",
            "cpf": cpf,
            "email": "bruno@exemplo.com",
            "curso": "IA",
            "turma_id": turma["id"],
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["campo"] == "cpf"


def test_cpf_aparece_mascarado(aluno):
    assert aluno["cpf"] == "***.982.247-**"


def test_turma_inexistente_no_corpo_e_erro_de_referencia(cliente):
    resposta = cliente.post(
        "/disciplinas",
        json={"nome": "POO", "carga_horaria": 60, "periodo_letivo": "2026.2", "turma_id": 999},
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "REFERENCIA_INVALIDA"


def test_professor_precisa_existir_no_auth(cliente, turma):
    resposta = cliente.post(
        "/disciplinas",
        json={
            "nome": "POO",
            "carga_horaria": 60,
            "periodo_letivo": "2026.2",
            "turma_id": turma["id"],
            "professor_id": 99,
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "PROFESSOR_INVALIDO"


def test_campo_obrigatorio_nao_pode_ser_apagado(cliente, turma):
    resposta = cliente.patch(f"/turmas/{turma['id']}", json={"nome": None})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "CAMPO_OBRIGATORIO"


def test_delete_de_aluno_e_logico(cliente, aluno):
    resposta = cliente.delete(f"/alunos/{aluno['id']}")

    assert resposta.json()["dados"]["status"] == "inativo"
    assert cliente.get(f"/alunos/{aluno['id']}").status_code == 200


def test_aluno_inexistente_responde_404(cliente):
    resposta = cliente.get("/alunos/999")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["codigo"] == "NAO_ENCONTRADO"


def test_busca_de_alunos_por_nome(cliente, aluno):
    corpo = cliente.get("/alunos", params={"busca": "beatriz"}).json()

    assert [a["id"] for a in corpo["dados"]] == [aluno["id"]]


def test_so_admin_reabre_turma_encerrada(cliente, turma, usuario):
    cliente.patch(f"/turmas/{turma['id']}", json={"status": "encerrada"})

    usuario.role = "coordenador"
    negado = cliente.patch(f"/turmas/{turma['id']}", json={"status": "ativa"})
    usuario.role = "admin"
    permitido = cliente.patch(f"/turmas/{turma['id']}", json={"status": "ativa"})

    assert negado.status_code == 403
    assert negado.json()["erro"]["codigo"] == "REABERTURA_RESTRITA"
    assert permitido.json()["dados"]["status"] == "ativa"
