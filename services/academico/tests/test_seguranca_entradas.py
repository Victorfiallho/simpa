"""Entradas hostis (RNF04): injeção de SQL, HTML em texto livre, parâmetros repetidos, CPF."""

import pytest

INJECOES = ["' OR '1'='1", "'; DROP TABLE alunos; --", '" OR ""="', "1; SELECT pg_sleep(5)"]


def codigo(resposta) -> str:
    return resposta.json()["erro"]["codigo"]


# ---------- Injeção de SQL ----------


@pytest.mark.parametrize("carga", INJECOES)
def test_busca_com_sql_injection_nao_acha_nada_e_nao_quebra_a_tabela(cliente, aluno, carga):
    resposta = cliente.get("/alunos", params={"busca": carga})

    assert resposta.status_code == 200
    assert resposta.json()["total_registros"] == 0
    # A tabela continua lá e a busca honesta continua achando o aluno.
    assert cliente.get("/alunos", params={"busca": "Ana"}).json()["total_registros"] == 1


@pytest.mark.parametrize("carga", INJECOES)
def test_ordenar_por_so_aceita_campos_da_lista(cliente, aluno, carga):
    resposta = cliente.get("/alunos", params={"ordenar_por": carga})

    assert resposta.status_code == 422
    assert codigo(resposta) == "ORDENACAO_INVALIDA"


@pytest.mark.parametrize("carga", INJECOES)
def test_matricula_na_rota_com_sql_injection_nao_existe(cliente, aluno, carga):
    resposta = cliente.get(f"/alunos/matricula/{carga}")

    assert resposta.status_code == 404


@pytest.mark.parametrize("filtro", ["turma_id", "status_", "limite", "pagina"])
def test_filtro_numerico_com_sql_injection_e_422(cliente, filtro):
    nome = "status" if filtro == "status_" else filtro
    resposta = cliente.get("/alunos", params={nome: "1 OR 1=1"})

    assert resposta.status_code == 422


def test_sql_injection_no_corpo_vira_texto_comum(cliente, turma):
    nome = "Robert'); DROP TABLE alunos;--"
    resposta = cliente.post(
        "/alunos",
        json={
            "matricula": "20269999",
            "nome_completo": nome,
            "cpf": "529.982.247-25",
            "email": "robert@exemplo.com",
            "curso": "Inteligência Artificial",
            "turma_id": turma["id"],
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["dados"]["nome_completo"] == nome  # gravado literalmente
    assert cliente.get("/alunos").json()["total_registros"] == 1


# ---------- Curingas do LIKE ----------


@pytest.mark.parametrize("curinga", ["%%", "A_a", "%na%", "a\\"])
def test_curingas_da_busca_valem_como_letras(cliente, aluno, curinga):
    resposta = cliente.get("/alunos", params={"busca": curinga})

    assert resposta.status_code == 200
    assert resposta.json()["total_registros"] == 0


# ---------- HTML e controle em texto livre ----------

HTML = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "Ana > Bruno", "A\x00B"]


@pytest.mark.parametrize("carga", HTML)
def test_turma_recusa_html_e_controle(cliente, carga):
    resposta = cliente.post(
        "/turmas",
        json={
            "nome": carga,
            "curso": "Inteligência Artificial",
            "periodo_letivo": "2026.2",
            "turno": "noturno",
        },
    )

    assert resposta.status_code == 422
    assert codigo(resposta) == "VALIDACAO"


@pytest.mark.parametrize("carga", HTML)
def test_aluno_recusa_html_no_nome(cliente, turma, carga):
    aluno_novo = {
        "matricula": "20260002",
        "nome_completo": "Bruno Souza",
        "cpf": "111.444.777-35",
        "email": "bruno@exemplo.com",
        "curso": "Inteligência Artificial",
        "turma_id": turma["id"],
    }
    resposta = cliente.post("/alunos", json={**aluno_novo, "nome_completo": f"Bruno {carga}"})

    assert resposta.status_code == 422


def test_edicao_tambem_recusa_html(cliente, turma):
    resposta = cliente.patch(f"/turmas/{turma['id']}", json={"nome": "<b>IA</b>"})

    assert resposta.status_code == 422
    assert cliente.get(f"/turmas/{turma['id']}").json()["dados"]["nome"] == turma["nome"]


def test_apostrofo_e_e_comercial_continuam_validos(cliente):
    resposta = cliente.post(
        "/turmas",
        json={
            "nome": "D'Ávila & Filhos",
            "curso": "Inteligência Artificial",
            "periodo_letivo": "2026.2",
            "turno": "noturno",
        },
    )

    assert resposta.status_code == 201
    assert resposta.json()["dados"]["nome"] == "D'Ávila & Filhos"


# ---------- Parâmetros repetidos ----------


@pytest.mark.parametrize(
    "consulta", ["limite=5&limite=500", "pagina=1&pagina=2", "turma_id=1&turma_id=2&turma_id=3"]
)
def test_parametro_repetido_e_recusado(cliente, consulta):
    resposta = cliente.get(f"/alunos?{consulta}")

    assert resposta.status_code == 400
    assert codigo(resposta) == "PARAMETRO_REPETIDO"


def test_parametros_diferentes_continuam_valendo(cliente, aluno):
    resposta = cliente.get("/alunos?limite=5&pagina=1&ordenar_por=id")

    assert resposta.status_code == 200


# ---------- CPF ----------


def test_cpf_so_sai_mascarado(cliente, aluno):
    cpf_inteiro = ("52998224725", "529.982.247-25")

    respostas = [
        cliente.get(f"/alunos/{aluno['id']}"),
        cliente.get("/alunos"),
        cliente.get(f"/alunos/matricula/{aluno['matricula']}"),
    ]

    for resposta in respostas:
        assert resposta.status_code == 200
        assert not any(c in resposta.text for c in cpf_inteiro)
        assert "***.982.247-**" in resposta.text
