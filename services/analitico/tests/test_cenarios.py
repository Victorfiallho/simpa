"""Cenários (RF07): margem para aprovação, projeção com regras ajustáveis e permissões."""

from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.clientes import academico
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from app.services.cenarios import Dados, Regras, calcular_margem, viabilidade
from tests.test_painel import inscricao

PADRAO = Regras()


def dados(n1, n2=None, freq="100.00", peso1="4", peso2="6"):
    return Dados(
        D(n1) if n1 is not None else None,
        D(peso1),
        D(n2) if n2 is not None else None,
        D(peso2),
        D(freq) if freq is not None else None,
    )


# ---------- Regras de entrada ----------


@pytest.mark.parametrize(
    "regras",
    [
        Regras(D(11), D(4), D(5)),
        Regras(D(6), D(-1), D(5)),
        Regras(D(6), D(7), D(5)),  # recuperação acima da aprovação
        Regras(D(6), D(4), D(12)),
    ],
)
def test_regras_invalidas(regras):
    from app.core.excecoes import RegraDeNegocioViolada

    with pytest.raises(RegraDeNegocioViolada) as erro:
        regras.validar()

    assert erro.value.codigo == "REGRAS_INVALIDAS"


def test_regras_padrao_sao_validas():
    PADRAO.validar()
    Regras(D(10), D(10), D(0)).validar()


# ---------- Margem: só a N1 lançada ----------


def test_nota_necessaria_na_n2():
    # N1 5,00 (peso 4): (6 × 10 − 5 × 4) ÷ 6 = 6,6667 → 6,67 (arredonda para cima)
    margem = calcular_margem(dados("5.00"), PADRAO)

    assert margem.modo == "n2"
    assert margem.necessario == D("6.67")
    assert margem.media_maxima == D("8.00")  # (5×4 + 10×6) ÷ 10
    assert viabilidade(margem) == (2, "exige_esforco")


def test_n1_alta_garante_aprovacao():
    margem = calcular_margem(dados("9.00"), Regras(D(3), D(2), D(1)))

    assert margem.necessario == D(0)
    assert viabilidade(margem) == (0, "garantida")


def test_n1_baixa_torna_a_aprovacao_direta_inviavel():
    # Com média de aprovação 9, N1 1,00: (9 × 10 − 1 × 4) ÷ 6 = 14,33, acima do máximo possível
    margem = calcular_margem(dados("1.00"), Regras(D(9), D(4), D(5)))

    assert margem.necessario > 10
    assert viabilidade(margem) == (4, "inviavel")


@pytest.mark.parametrize(
    ("n1", "codigo"),
    [("7.00", "alcancavel"), ("5.00", "exige_esforco"), ("2.00", "dificil")],
)
def test_faixas_de_viabilidade_na_n2(n1, codigo):
    assert viabilidade(calcular_margem(dados(n1), PADRAO))[1] == codigo


def test_hipotese_na_n2():
    margem = calcular_margem(dados("5.00"), PADRAO, hipotese=D("7.00"))

    assert margem.hipotese_media == D("6.20")
    assert margem.hipotese_resultado == "direta"
    assert calcular_margem(dados("5.00"), PADRAO, D("4.00")).hipotese_resultado == "recuperacao"
    assert calcular_margem(dados("2.00"), PADRAO, D("2.00")).hipotese_resultado == "rep_nota"


def test_hipotese_com_frequencia_baixa_reprova_por_frequencia():
    margem = calcular_margem(dados("8.00", freq="70.00"), PADRAO, hipotese=D("10"))

    assert margem.hipotese_resultado == "rep_freq"


# ---------- Margem: N1 e N2 lançadas ----------


def test_aprovado_direto():
    margem = calcular_margem(dados("7.00", "8.00"), PADRAO)

    assert (margem.modo, margem.media) == ("aprovado", D("7.60"))
    assert viabilidade(margem) == (0, "aprovado_direto")


def test_recuperacao_pede_nota_no_exame():
    # Média (4×4 + 5×6) ÷ 10 = 4,60; exame mínimo: 2 × 5 − 4,60 = 5,40
    margem = calcular_margem(dados("4.00", "5.00"), PADRAO)

    assert (margem.modo, margem.media, margem.necessario) == ("exame", D("4.60"), D("5.40"))
    assert margem.exame_possivel is True
    assert viabilidade(margem) == (2, "exige_esforco")


def test_hipotese_no_exame():
    margem = calcular_margem(dados("4.00", "5.00"), PADRAO, hipotese=D("6.00"))

    assert margem.hipotese_media == D("5.30")  # (4,60 + 6) ÷ 2
    assert margem.hipotese_resultado == "recuperado"
    abaixo = calcular_margem(dados("4.00", "5.00"), PADRAO, hipotese=D("4.00"))
    assert abaixo.hipotese_resultado == "rep_nota"


def test_exame_impossivel_com_regra_dura():
    regras = Regras(D(9), D(4), D(9))  # exame precisaria de 2 × 9 − 4,60 = 13,40

    margem = calcular_margem(dados("4.00", "5.00"), regras)

    assert margem.exame_possivel is False
    assert viabilidade(margem) == (4, "inviavel")


def test_media_abaixo_da_minima_reprova_por_nota():
    margem = calcular_margem(dados("2.00", "3.00"), PADRAO)

    assert margem.modo == "rep_nota"
    assert viabilidade(margem) == (5, "reprovacao_nota")


def test_frequencia_baixa_domina_a_viabilidade():
    margem = calcular_margem(dados("4.00", "5.00", freq="70.00"), PADRAO)

    assert viabilidade(margem) == (5, "reprovacao_frequencia")


def test_sem_notas():
    margem = calcular_margem(dados(None), PADRAO)

    assert margem.modo == "sem_dados"
    assert viabilidade(margem) == (0, "sem_dados")


# ---------- Rotas ----------


def cenario():
    return [
        inscricao(1, 1, "Ana Lima", "EST", [("N1", "9.00", "4"), ("N2", "9.00", "6")]),  # direta
        inscricao(2, 2, "Bruno Costa", "EST", [("N1", "5.00", "4"), ("N2", "4.50", "6")]),  # exame
        inscricao(
            3, 3, "Clara Souza", "EST", [("N1", "2.00", "4"), ("N2", "3.00", "6")]
        ),  # reprova
        inscricao(4, 4, "Davi Reis", "EST", [("N1", "5.00", "4")]),  # só N1
        inscricao(5, 5, "Eva Dias", "EST"),  # sem dados
        inscricao(
            6, 3, "Clara Souza", "ALG", [("N1", "9.00", "4"), ("N2", "9.00", "6")], faltas=12
        ),
    ]


@pytest.fixture
def api(monkeypatch):
    estado = {"papel": "coordenador", "inscricoes": cenario()}
    monkeypatch.setattr(academico, "buscar_inscricoes", lambda **_: estado["inscricoes"])
    monkeypatch.setattr(
        academico,
        "buscar_inscricao",
        lambda id_: next(i for i in estado["inscricoes"] if i.id == id_),
    )
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(id=1, role=estado["papel"])
    estado["cliente"] = TestClient(app)
    yield estado
    app.dependency_overrides.clear()


def projetar(api, **params):
    resposta = api["cliente"].get("/cenarios/projecao", params=params)
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["dados"]


def test_projecao_com_n1_e_n2_lancadas(api):
    dados = projetar(api, base="atual")

    assert dados["contagem"] == {
        "direta": 1,
        "recuperacao": 2,  # Bruno (média 4,70) e Davi (N2 estimada pela tendência)
        "rep_nota": 1,
        "rep_freq": 1,
        "sem_dados": 1,
    }
    assert dados["inscricoes_projetadas"] == 5  # a inscrição sem dados não conta
    assert dados["retencao_percentual"] == "80.00"
    assert dados["alunos"] == {"aprovados_em_tudo": 1, "com_recuperacao": 2, "com_reprovacao": 1}


def test_projecao_a_partir_da_n1_estima_a_n2_pela_tendencia(api):
    dados = projetar(api, base="n1")

    # Só a N1 conta. Variação média da disciplina (N2 − N1): Ana 0, Bruno −0,5, Clara +1 → +0,17
    variacao = {v["disciplina_nome"]: v["variacao"] for v in dados["variacao_por_disciplina"]}
    assert variacao["Estatística"] == "0.17"
    assert dados["contagem"]["sem_dados"] == 1


def test_regras_mais_duras_aumentam_a_retencao(api):
    padrao = projetar(api, base="atual")
    dura = projetar(api, base="atual", aprovacao=9.5, recuperacao=6)

    assert D(dura["retencao_percentual"]) > D(padrao["retencao_percentual"])
    assert D(dura["regras"]["aprovacao"]) == D("9.5")


def test_metas_listam_alunos_em_risco_do_mais_grave_ao_menos(api):
    metas = projetar(api, base="atual")["metas"]

    nomes = [m["aluno_nome"] for m in metas]
    assert "Ana Lima" not in nomes  # aprovada direto, sem meta
    assert "Eva Dias" not in nomes  # sem dados
    assert metas[0]["viabilidade"] in {"reprovacao_nota", "reprovacao_frequencia"}
    assert all(m["meta"] for m in metas)


def test_limite_de_metas(api):
    dados = projetar(api, base="atual", limite_metas=1)

    assert len(dados["metas"]) == 1
    assert dados["total_metas"] >= 2


@pytest.mark.parametrize(
    "params",
    [
        {"aprovacao": 11},
        {"recuperacao": -1},
        {"final": "abc"},
        {"base": "outra"},
    ],
)
def test_parametros_invalidos_na_projecao_sao_422(api, params):
    resposta = api["cliente"].get("/cenarios/projecao", params=params)

    assert resposta.status_code == 422


def test_recuperacao_maior_que_aprovacao_e_422(api):
    resposta = api["cliente"].get("/cenarios/projecao", params={"aprovacao": 5, "recuperacao": 7})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "REGRAS_INVALIDAS"


def test_margem_de_uma_inscricao_com_hipotese(api):
    resposta = api["cliente"].get("/cenarios/margem/4", params={"base": "atual", "hipotese": 7})

    dados = resposta.json()["dados"]
    assert dados["modo"] == "n2"
    assert dados["necessario"] == "6.67"
    assert dados["viabilidade"] == "exige_esforco"
    assert dados["hipotese_media"] == "6.20"
    assert dados["hipotese_resultado"] == "direta"
    assert dados["meta"].startswith("Precisa de 6,67 na N2")


def test_margem_do_exame(api):
    dados = api["cliente"].get("/cenarios/margem/2").json()["dados"]

    assert dados["modo"] == "exame"
    assert dados["meta"].startswith("Média 4,70: recuperação. Precisa de 5,30 no exame")


def test_hipotese_fora_da_faixa_e_422(api):
    assert api["cliente"].get("/cenarios/margem/4", params={"hipotese": 11}).status_code == 422


@pytest.mark.parametrize("papel", ["professor"])
def test_so_gestao_acessa_os_cenarios(api, papel):
    api["papel"] = papel

    assert api["cliente"].get("/cenarios/projecao").status_code == 403
    assert api["cliente"].get("/cenarios/margem/1").status_code == 403


def test_admin_tambem_acessa(api):
    api["papel"] = "admin"

    assert api["cliente"].get("/cenarios/projecao").status_code == 200
