"""Entradas hostis no analítico (RNF04): SQL, HTML em texto livre, parâmetros repetidos, PII."""

from datetime import date

import pytest

from tests.test_alertas import estado  # noqa: F401  (acadêmico e banco simulados)
from tests.test_painel import inscricao

HTML = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "a > b", "A\x00B"]
SQL = "x'); DROP TABLE acompanhamento; --"
HOJE = date.today().isoformat()


def codigo(resposta) -> str:
    return resposta.json()["erro"]["codigo"]


def acompanhar(cliente, observacao):
    return cliente.post(
        "/acompanhamentos",
        json={"aluno_id": 1, "tipo": "contato", "data": HOJE, "observacao": observacao},
    )


# ---------- Texto livre ----------


@pytest.mark.parametrize("carga", HTML)
def test_observacao_do_acompanhamento_recusa_html(estado, carga):  # noqa: F811
    resposta = acompanhar(estado["cliente"], f"Conversa {carga}")

    assert resposta.status_code == 422
    assert codigo(resposta) == "VALIDACAO"


def test_sql_na_observacao_vira_texto_comum(estado):  # noqa: F811
    resposta = acompanhar(estado["cliente"], SQL)

    assert resposta.status_code == 201
    assert resposta.json()["dados"]["observacao"] == SQL
    # Nada foi apagado: o acompanhamento voltou na listagem.
    lista = estado["cliente"].get("/acompanhamentos", params={"aluno_id": 1}).json()["dados"]
    assert [a["observacao"] for a in lista] == [SQL]


def test_acompanhamento_aceita_apostrofo_e_e_comercial(estado):  # noqa: F811
    resposta = acompanhar(estado["cliente"], "Falou com o pai: D'Ávila & família")

    assert resposta.status_code == 201


# ---------- Parâmetros repetidos ----------


@pytest.mark.parametrize(
    "rota",
    [
        "/alertas?turma_id=1&turma_id=2",
        "/alertas?tipo=queda&tipo=abandono",
        "/painel?periodo_letivo=2026.1&periodo_letivo=2026.2",
        "/cenarios/projecao?aprovacao=6&aprovacao=0",
    ],
)
def test_parametro_repetido_e_recusado(estado, rota):  # noqa: F811
    resposta = estado["cliente"].get(rota)

    assert resposta.status_code == 400
    assert codigo(resposta) == "PARAMETRO_REPETIDO"


# ---------- Injeção de SQL em filtros e caminhos ----------


@pytest.mark.parametrize("filtro", ["turma_id", "disciplina_id"])
def test_filtro_numerico_com_sql_e_422(estado, filtro):  # noqa: F811
    resposta = estado["cliente"].get("/alertas", params={filtro: "1 OR 1=1"})

    assert resposta.status_code == 422


def test_filtro_de_texto_com_sql_nao_quebra_nem_vaza(estado):  # noqa: F811
    resposta = estado["cliente"].get("/alertas", params={"tipo": "queda' OR '1'='1"})

    assert resposta.status_code == 422


def test_periodo_com_sql_so_e_repassado_como_parametro(estado):  # noqa: F811
    resposta = estado["cliente"].get("/painel", params={"periodo_letivo": "2026.2' OR '1'='1"})

    assert resposta.status_code in (200, 422)  # nunca 500


# ---------- Dados pessoais ----------


def test_nenhuma_resposta_de_analise_traz_email_nem_cpf(estado):  # noqa: F811
    estado["inscricoes"] = [
        inscricao(1, 1, "Ana Lima", "EST", [("N1", "8.00", "4"), ("N2", "3.00", "6")], faltas=9)
    ]
    cliente = estado["cliente"]

    respostas = [
        cliente.get("/painel"),
        cliente.get("/alertas"),
        cliente.get("/cenarios/projecao"),
        cliente.post("/copiloto/perguntas", json={"pergunta": "Como está a Ana Lima?"}),
    ]

    for resposta in respostas:
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.text.lower()
        assert "@" not in corpo
        assert '"email"' not in corpo
        assert "cpf" not in corpo


def test_copiloto_nao_devolve_o_texto_digitado(estado):  # noqa: F811
    resposta = estado["cliente"].post(
        "/copiloto/perguntas", json={"pergunta": "alunos de <script>alert(1)</script> em risco"}
    )

    assert resposta.status_code == 200
    assert "<script>" not in resposta.text
