"""Perfis de acesso do acadêmico (D03): quem pode cadastrar, lançar e consultar o quê."""

import pytest

from tests.conftest import PROFESSOR_VALIDO

NOTA = {"tipo_avaliacao": "prova", "periodo_avaliacao": "N1", "nota": 7, "peso": 1}
FREQUENCIA = {"periodo_avaliacao": "N1", "aulas_previstas": 32, "faltas": 2}


def como(usuario, role: str, id_: int = 1) -> None:
    usuario.role = role
    usuario.id = id_


def lancar_nota(cliente, inscricao) -> dict:
    corpo = {"inscricao_id": inscricao["id"], **NOTA}
    return cliente.post("/avaliacoes", json=corpo).json()["dados"]


def lancar_frequencia(cliente, inscricao) -> dict:
    corpo = {"inscricao_id": inscricao["id"], **FREQUENCIA}
    return cliente.post("/frequencias", json=corpo).json()["dados"]


def codigo(resposta) -> str:
    return resposta.json()["erro"]["codigo"]


@pytest.fixture
def aluno_novo(turma):
    return {
        "matricula": "20260002",
        "nome_completo": "Bruno Souza",
        "cpf": "111.444.777-35",
        "email": "bruno@exemplo.com",
        "curso": "Inteligência Artificial",
        "turma_id": turma["id"],
    }


# ---------- Cadastros: admin e coordenador ----------


def test_coordenador_cadastra_aluno(cliente, usuario, aluno_novo):
    como(usuario, "coordenador")

    assert cliente.post("/alunos", json=aluno_novo).status_code == 201


def test_professor_nao_cadastra_aluno(cliente, usuario, aluno_novo):
    como(usuario, "professor", PROFESSOR_VALIDO)

    resposta = cliente.post("/alunos", json=aluno_novo)

    assert resposta.status_code == 403
    assert codigo(resposta) == "ACESSO_NEGADO"


@pytest.mark.parametrize(
    ("metodo", "rota"),
    [
        ("patch", "/turmas/{turma}"),
        ("delete", "/turmas/{turma}"),
        ("patch", "/disciplinas/{disciplina}"),
        ("delete", "/disciplinas/{disciplina}"),
        ("patch", "/alunos/{aluno}"),
        ("delete", "/alunos/{aluno}"),
        ("patch", "/inscricoes/{inscricao}"),
        ("delete", "/inscricoes/{inscricao}"),
    ],
)
def test_professor_nao_altera_cadastros(
    cliente, usuario, turma, disciplina, aluno, inscricao, metodo, rota
):
    como(usuario, "professor", PROFESSOR_VALIDO)
    caminho = rota.format(
        turma=turma["id"],
        disciplina=disciplina["id"],
        aluno=aluno["id"],
        inscricao=inscricao["id"],
    )

    resposta = cliente.request(metodo.upper(), caminho, json={} if metodo == "patch" else None)

    assert resposta.status_code == 403
    assert codigo(resposta) == "ACESSO_NEGADO"


def test_professor_nao_cria_inscricao(cliente, usuario, aluno, disciplina):
    como(usuario, "professor", PROFESSOR_VALIDO)

    resposta = cliente.post(
        "/inscricoes", json={"aluno_id": aluno["id"], "disciplina_id": disciplina["id"]}
    )

    assert resposta.status_code == 403


def test_coordenador_cria_inscricao(cliente, usuario, aluno, disciplina):
    como(usuario, "coordenador")

    resposta = cliente.post(
        "/inscricoes", json={"aluno_id": aluno["id"], "disciplina_id": disciplina["id"]}
    )

    assert resposta.status_code == 201


# ---------- Lançamentos: admin e professor da disciplina ----------


def test_coordenador_nao_lanca_nota_nem_frequencia(cliente, usuario, inscricao):
    como(usuario, "coordenador")

    nota = cliente.post("/avaliacoes", json={"inscricao_id": inscricao["id"], **NOTA})
    freq = cliente.post("/frequencias", json={"inscricao_id": inscricao["id"], **FREQUENCIA})

    assert (nota.status_code, freq.status_code) == (403, 403)
    assert codigo(nota) == "ACESSO_NEGADO"


def test_professor_lanca_nota_e_frequencia_na_propria_disciplina(cliente, usuario, inscricao):
    como(usuario, "professor", PROFESSOR_VALIDO)

    nota = cliente.post("/avaliacoes", json={"inscricao_id": inscricao["id"], **NOTA})
    freq = cliente.post("/frequencias", json={"inscricao_id": inscricao["id"], **FREQUENCIA})

    assert (nota.status_code, freq.status_code) == (201, 201)


def test_professor_nao_lanca_em_disciplina_de_outro(cliente, usuario, inscricao):
    como(usuario, "professor", 99)

    nota = cliente.post("/avaliacoes", json={"inscricao_id": inscricao["id"], **NOTA})
    freq = cliente.post("/frequencias", json={"inscricao_id": inscricao["id"], **FREQUENCIA})

    assert (nota.status_code, freq.status_code) == (403, 403)
    assert codigo(nota) == "DISCIPLINA_FORA_DO_ESCOPO"


def test_professor_de_fora_nao_edita_nem_apaga_lancamentos(cliente, usuario, inscricao):
    nota = lancar_nota(cliente, inscricao)
    freq = lancar_frequencia(cliente, inscricao)
    como(usuario, "professor", 99)

    respostas = [
        cliente.patch(f"/avaliacoes/{nota['id']}", json={"nota": 9}),
        cliente.delete(f"/avaliacoes/{nota['id']}"),
        cliente.patch(f"/frequencias/{freq['id']}", json={"faltas": 0}),
        cliente.delete(f"/frequencias/{freq['id']}"),
    ]

    assert [r.status_code for r in respostas] == [403, 403, 403, 403]


def test_professor_da_disciplina_edita_a_propria_nota(cliente, usuario, inscricao):
    nota = lancar_nota(cliente, inscricao)
    como(usuario, "professor", PROFESSOR_VALIDO)

    resposta = cliente.patch(f"/avaliacoes/{nota['id']}", json={"nota": 9})

    assert resposta.status_code == 200


# ---------- Consultas: o professor só vê o que é seu ----------


def test_professor_lista_so_as_proprias_disciplinas(cliente, usuario, disciplina):
    como(usuario, "professor", PROFESSOR_VALIDO)
    assert cliente.get("/disciplinas").json()["total_registros"] == 1

    como(usuario, "professor", 99)
    assert cliente.get("/disciplinas").json()["total_registros"] == 0


def test_professor_nao_abre_disciplina_de_outro(cliente, usuario, disciplina):
    como(usuario, "professor", 99)

    resposta = cliente.get(f"/disciplinas/{disciplina['id']}")

    assert resposta.status_code == 403
    assert codigo(resposta) == "DISCIPLINA_FORA_DO_ESCOPO"


def test_professor_ve_so_alunos_das_suas_disciplinas(cliente, usuario, aluno, inscricao):
    como(usuario, "professor", PROFESSOR_VALIDO)
    assert cliente.get("/alunos").json()["total_registros"] == 1
    assert cliente.get(f"/alunos/{aluno['id']}").status_code == 200
    assert cliente.get(f"/alunos/matricula/{aluno['matricula']}").status_code == 200

    como(usuario, "professor", 99)
    assert cliente.get("/alunos").json()["total_registros"] == 0
    negado = cliente.get(f"/alunos/{aluno['id']}")
    assert negado.status_code == 403
    assert codigo(negado) == "ALUNO_FORA_DO_ESCOPO"
    assert cliente.get(f"/alunos/matricula/{aluno['matricula']}").status_code == 403


def test_professor_ve_so_inscricoes_notas_e_frequencias_proprias(cliente, usuario, inscricao):
    nota = lancar_nota(cliente, inscricao)
    freq = lancar_frequencia(cliente, inscricao)

    como(usuario, "professor", PROFESSOR_VALIDO)
    for rota in ("/inscricoes", "/avaliacoes", "/frequencias"):
        assert cliente.get(rota).json()["total_registros"] == 1
    assert cliente.get(f"/inscricoes/{inscricao['id']}").status_code == 200

    como(usuario, "professor", 99)
    for rota in ("/inscricoes", "/avaliacoes", "/frequencias"):
        assert cliente.get(rota).json()["total_registros"] == 0
    assert cliente.get(f"/inscricoes/{inscricao['id']}").status_code == 403
    assert cliente.get(f"/avaliacoes/{nota['id']}").status_code == 403
    assert cliente.get(f"/frequencias/{freq['id']}").status_code == 403


@pytest.mark.parametrize("role", ["admin", "coordenador"])
def test_admin_e_coordenador_veem_tudo(cliente, usuario, aluno, inscricao, role):
    como(usuario, role, 99)

    assert cliente.get("/disciplinas").json()["total_registros"] == 1
    assert cliente.get("/alunos").json()["total_registros"] == 1
    assert cliente.get(f"/alunos/{aluno['id']}").status_code == 200
    assert cliente.get("/inscricoes").json()["total_registros"] == 1


# ---------- Reabertura (D10) ----------


def test_coordenador_nao_reabre_disciplina_encerrada(cliente, usuario, disciplina):
    cliente.patch(f"/disciplinas/{disciplina['id']}", json={"status": "encerrada"})
    como(usuario, "coordenador")

    resposta = cliente.patch(f"/disciplinas/{disciplina['id']}", json={"status": "ativa"})

    assert resposta.status_code == 403
    assert codigo(resposta) == "REABERTURA_RESTRITA"

    como(usuario, "admin")
    assert (
        cliente.patch(f"/disciplinas/{disciplina['id']}", json={"status": "ativa"}).status_code
        == 200
    )
