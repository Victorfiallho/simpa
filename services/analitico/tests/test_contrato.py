"""Contrato da API do analítico (RF08, RNF14): envelope, erros padronizados e OpenAPI honesto."""

from datetime import date

from app.main import app
from tests.test_alertas import estado  # noqa: F401  (acadêmico e banco simulados)

ENVELOPE = {"status", "mensagem", "dados", "erro"}
OPERACOES = {"get", "post", "put", "patch", "delete"}


def operacoes():
    for caminho, itens in app.openapi()["paths"].items():
        for metodo, operacao in itens.items():
            if metodo in OPERACOES:
                yield caminho, metodo, operacao


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
        if c != "/health" and not {"401", "403"} <= set(o["responses"])
    ]

    assert faltando == []


def test_rotas_com_id_no_caminho_documentam_404():
    faltando = [
        f"{m.upper()} {c}" for c, m, o in operacoes() if "{" in c and "404" not in o["responses"]
    ]

    assert faltando == []


def test_erros_apontam_para_o_envelope_padrao():
    esquema = app.openapi()
    erro = esquema["paths"]["/alertas"]["get"]["responses"]["403"]

    assert erro["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErroPadrao"
    }
    assert set(esquema["components"]["schemas"]["ErroPadrao"]["properties"]) == ENVELOPE
    assert "HTTPValidationError" not in esquema["components"]["schemas"]


# ---------- Respostas reais ----------


def test_painel_segue_o_envelope(estado):  # noqa: F811
    corpo = estado["cliente"].get("/painel").json()

    assert set(corpo) == ENVELOPE
    assert corpo["status"] == "sucesso" and corpo["erro"] is None
    assert {"total_alunos", "media_geral", "contagem", "achados", "alunos"} <= set(corpo["dados"])


def test_alertas_seguem_o_envelope(estado):  # noqa: F811
    corpo = estado["cliente"].get("/alertas").json()

    assert set(corpo) == ENVELOPE
    assert set(corpo["dados"]) == {"resumo", "alertas"}
    assert [r["tipo"] for r in corpo["dados"]["resumo"]] == ["queda", "frequencia", "abandono"]


def test_projecao_segue_o_envelope(estado):  # noqa: F811
    corpo = estado["cliente"].get("/cenarios/projecao").json()

    assert set(corpo) == ENVELOPE
    assert {"regras", "contagem", "retencao_percentual", "metas"} <= set(corpo["dados"])


def test_criar_acompanhamento_responde_201(estado):  # noqa: F811
    resposta = estado["cliente"].post(
        "/acompanhamentos",
        json={
            "aluno_id": 1,
            "tipo": "contato",
            "data": date.today().isoformat(),
            "observacao": "Conversa realizada.",
        },
    )

    assert resposta.status_code == 201
    assert set(resposta.json()) == ENVELOPE
    assert {"id", "aluno_id", "tipo", "observacao"} <= set(resposta.json()["dados"])


def test_erro_422_lista_os_campos_invalidos(estado):  # noqa: F811
    resposta = estado["cliente"].post("/acompanhamentos", json={"aluno_id": 1})

    erro = resposta.json()["erro"]
    assert resposta.status_code == 422
    assert erro["codigo"] == "VALIDACAO"
    assert all({"campo", "regra", "mensagem"} == set(c) for c in erro["campos"])


def test_erro_403_segue_o_envelope(estado):  # noqa: F811
    estado["papel"] = "professor"

    resposta = estado["cliente"].get("/alertas")

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "ACESSO_NEGADO"
    assert set(resposta.json()) == ENVELOPE


def test_regras_de_cenario_invalidas_dao_422_com_codigo_proprio(estado):  # noqa: F811
    resposta = estado["cliente"].get(
        "/cenarios/projecao", params={"aprovacao": 3, "recuperacao": 4}
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "REGRAS_INVALIDAS"
