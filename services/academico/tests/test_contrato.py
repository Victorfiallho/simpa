"""Contrato da API (RF08, RF10, RNF14): envelope, erros padronizados e OpenAPI honesto."""

import pytest

from app.main import app

ENVELOPE = {"status", "mensagem", "dados", "erro"}
LISTAGEM = ENVELOPE | {"pagina", "limite", "total_registros"}
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


def test_rotas_que_recebem_corpo_documentam_422_e_201_ou_200():
    for caminho, metodo, operacao in operacoes():
        if metodo in {"post", "patch", "put"}:
            assert "422" in operacao["responses"], f"{metodo} {caminho}"
            assert {"200", "201"} & set(operacao["responses"]), f"{metodo} {caminho}"


def test_erros_apontam_para_o_envelope_padrao():
    esquema = app.openapi()
    erro = esquema["paths"]["/turmas/{turma_id}"]["get"]["responses"]["404"]

    assert erro["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErroPadrao"
    }
    propriedades = esquema["components"]["schemas"]["ErroPadrao"]["properties"]
    assert set(propriedades) == ENVELOPE
    assert "HTTPValidationError" not in esquema["components"]["schemas"]


# ---------- Respostas reais ----------


def test_criar_responde_201_com_envelope(cliente):
    resposta = cliente.post(
        "/turmas",
        json={
            "nome": "IA",
            "curso": "Inteligência Artificial",
            "periodo_letivo": "2026.2",
            "turno": "noturno",
        },
    )

    corpo = resposta.json()
    assert resposta.status_code == 201
    assert set(corpo) == ENVELOPE
    assert corpo["status"] == "sucesso" and corpo["erro"] is None
    assert {"id", "nome", "curso", "periodo_letivo", "turno"} <= set(corpo["dados"])


def test_listagem_traz_paginacao(cliente, turma):
    corpo = cliente.get("/turmas").json()

    assert set(corpo) == LISTAGEM
    assert isinstance(corpo["dados"], list)
    assert (corpo["pagina"], corpo["limite"], corpo["total_registros"]) == (1, 20, 1)


def test_erro_404_segue_o_envelope(cliente):
    resposta = cliente.get("/turmas/9999")

    corpo = resposta.json()
    assert resposta.status_code == 404
    assert set(corpo) == ENVELOPE
    assert corpo["status"] == "erro" and corpo["dados"] is None
    assert corpo["erro"]["codigo"] == "NAO_ENCONTRADO"
    assert corpo["erro"]["mensagem"]


def test_erro_422_lista_os_campos_invalidos(cliente):
    resposta = cliente.post("/turmas", json={"nome": ""})

    erro = resposta.json()["erro"]
    assert resposta.status_code == 422
    assert erro["codigo"] == "VALIDACAO"
    assert erro["campos"]
    assert all({"campo", "regra", "mensagem"} == set(c) for c in erro["campos"])


@pytest.mark.parametrize("rota", ["/turmas", "/alunos", "/disciplinas", "/inscricoes"])
def test_erro_403_segue_o_envelope(cliente, usuario, rota):
    usuario.role = "professor"
    resposta = cliente.post(rota, json={})

    assert resposta.status_code == 403
    assert resposta.json()["erro"]["codigo"] == "ACESSO_NEGADO"
    assert set(resposta.json()) == ENVELOPE
