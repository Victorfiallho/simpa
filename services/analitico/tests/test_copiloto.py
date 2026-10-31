"""Copiloto (RF07): reconhece a intenção por regras e responde com os números do painel."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clientes import academico
from app.core.database import Base, get_db
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from app.services.copiloto import condicao, interpretar, normalizar
from tests.test_painel import inscricao

# Cenário (EST = Estatística, ALG = Álgebra, POO):
#   Ana Lima   — EST 4,60 (em risco), ALG 8,60            → em risco
#   Bruno Costa — EST 3,00 e frequência 62,5% (em risco)  → em risco, mais urgente
#   Clara Souza — EST 8,60, POO 9,00                      → sem risco
BOM = [("N1", "8.00", "4"), ("N2", "9.00", "6")]


def cenario():
    return [
        inscricao(1, 1, "Ana Lima", "EST", [("N1", "4.00", "4"), ("N2", "5.00", "6")]),
        inscricao(2, 1, "Ana Lima", "ALG", BOM),
        inscricao(
            3, 2, "Bruno Costa", "EST", [("N1", "3.00", "4"), ("N2", "3.00", "6")], faltas=12
        ),
        inscricao(4, 3, "Clara Souza", "EST", BOM),
        inscricao(5, 3, "Clara Souza", "POO", [("N1", "9.00", "4"), ("N2", "9.00", "6")]),
    ]


@pytest.fixture
def api(monkeypatch):
    estado = {"papel": "coordenador"}
    monkeypatch.setattr(academico, "buscar_inscricoes", lambda **_: cenario())
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessoes = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        with sessoes() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(id=1, role=estado["papel"])
    estado["http"] = TestClient(app)
    yield estado
    app.dependency_overrides.clear()
    engine.dispose()


def perguntar(api, texto):
    resposta = api["http"].post("/copiloto/perguntas", json={"pergunta": texto})
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()["dados"]


# ---------- Interpretação ----------


def test_normalizar_tira_acentos_e_pontuacao():
    assert (
        normalizar("  Quem tirou ABAIXO de 5, em Álgebra?? ")
        == "quem tirou abaixo de 5, em algebra"
    )


@pytest.mark.parametrize(
    ("texto", "palavras", "esperado"),
    [
        ("quem tirou abaixo de 5", "tirou|nota|media", ("<", "5")),
        ("media menor que 6,5", "tirou|nota|media", ("<", "6.5")),
        ("presenca acima de 90", "presenca|frequencia", (">", "90")),
        ("quem tirou 5", "tirou|nota|media", None),
    ],
)
def test_condicoes_numericas(texto, palavras, esperado):
    c = condicao(texto, palavras)

    assert (None if c is None else (c.operador, str(c.valor))) == esperado


@pytest.mark.parametrize(
    ("pergunta", "intencao"),
    [
        ("Gere um resumo para a reunião de colegiado", "resumo"),
        ("Quais alunos precisam de monitoria urgente?", "monitoria"),
        ("Quem tirou abaixo de 5 em Estatística?", "filtro"),
        ("presença menor que 70%", "filtro"),
        ("Quantos alunos estão em risco?", "contagem"),
        ("Como está o desempenho da turma?", "situacao"),
        ("Quais alertas de abandono existem?", "alertas"),
        ("Quantos podem ficar em recuperação?", "projecao"),
        ("Quantos desistiram do curso?", "fora_do_escopo"),
        ("bom dia", None),
    ],
)
def test_reconhece_a_intencao(pergunta, intencao):
    assert interpretar(pergunta, cenario()).intencao == intencao


def test_reconhece_disciplina_pelo_nome_ou_sigla():
    por_nome = interpretar("situação em Estatística", cenario())
    por_codigo = interpretar("situação em alg", cenario())

    assert (por_nome.disciplina_nome, por_codigo.disciplina_nome) == ("Estatística", "Álgebra")


def test_reconhece_aluno_por_nome_e_por_matricula():
    por_nome = interpretar("como está a Ana Lima", cenario())
    por_matricula = interpretar("situação do aluno 20260002", cenario())

    assert por_nome.aluno.aluno.nome_completo == "Ana Lima"
    assert por_matricula.aluno.aluno.nome_completo == "Bruno Costa"


def test_um_so_nome_nao_basta_para_achar_aluno():
    assert interpretar("e o Bruno?", cenario()).aluno is None


# ---------- Respostas ----------


def test_monitoria_prioriza_o_mais_urgente(api):
    dados = perguntar(api, "Quais alunos precisam de monitoria urgente?")

    assert dados["intencao"] == "monitoria"
    assert dados["total_itens"] == 2
    assert [i["aluno_nome"] for i in dados["itens"]] == ["Bruno Costa", "Ana Lima"]
    assert "Estatística (2)" in dados["texto"]
    assert dados["itens"][0]["detalhe"].startswith("Estatística 3,00")


def test_filtro_por_nota_e_frequencia(api):
    dados = perguntar(api, "Quem tirou abaixo de 5 em Estatística e tem presença menor que 70%?")

    assert dados["intencao"] == "filtro"
    assert [i["aluno_nome"] for i in dados["itens"]] == ["Bruno Costa"]
    assert "média abaixo de 5" in dados["texto"] and "frequência abaixo de 70%" in dados["texto"]
    assert dados["recorte"].endswith("Estatística")


def test_filtro_sem_resultado(api):
    dados = perguntar(api, "quem tirou abaixo de 1")

    assert dados["itens"] == []
    assert dados["texto"].startswith("Nenhuma inscrição com média abaixo de 1")


def test_situacao_de_um_aluno(api):
    dados = perguntar(api, "Como está a Ana Lima?")

    assert dados["intencao"] == "aluno"
    assert "situação em risco" in dados["texto"]
    assert {i["detalhe"].split(":")[0] for i in dados["itens"]} == {"Estatística", "Álgebra"}


def test_aluno_nao_encontrado(api):
    dados = perguntar(api, "situação do aluno 99999999")

    assert dados["texto"].startswith("Não encontrei esse aluno")


def test_contagem_por_situacao(api):
    dados = perguntar(api, "Quantos alunos estão em risco?")

    assert "3 alunos ativos: 2 em risco, 0 em atenção, 1 sem risco" in dados["texto"]


def test_contagem_respeita_a_disciplina(api):
    dados = perguntar(api, "Quantos alunos em POO estão em risco?")

    assert "1 alunos ativos: 0 em risco" in dados["texto"]


def test_situacao_geral(api):
    dados = perguntar(api, "Como está o desempenho da turma?")

    assert dados["intencao"] == "situacao"
    assert "2 aluno(s) em risco" in dados["texto"]


def test_resumo_traz_secoes_e_texto_para_copiar(api):
    dados = perguntar(api, "Gere um resumo do desempenho da turma para o colegiado")

    titulos = [s["titulo"] for s in dados["secoes"]]
    assert titulos[:2] == ["Visão geral", "Situação dos alunos"]
    assert "Alunos prioritários" in titulos and "Encaminhamentos sugeridos" in titulos
    assert dados["texto_completo"].startswith("RESUMO DO DESEMPENHO PARA O COLEGIADO")
    assert "Bruno Costa" in dados["texto_completo"]
    assert "Oferecer monitoria em Estatística" in dados["texto_completo"]


def test_assunto_desconhecido_diz_o_que_existe(api):
    dados = perguntar(api, "quais alunos de Culinária precisam de monitoria?")

    assert dados["intencao"] == "desconhecido"
    assert "culinaria" in dados["texto"]
    assert "Estatística" in dados["texto"]
    assert dados["sugestoes"]


def test_nao_entendeu_oferece_ajuda(api):
    dados = perguntar(api, "me conta uma piada")

    assert dados["intencao"] == "ajuda"
    assert dados["texto"].startswith("Não entendi bem a pergunta")
    assert dados["sugestoes"]


def test_responde_sobre_alertas_ativos(api):
    dados = perguntar(api, "quais alertas estão pendentes?")

    assert dados["intencao"] == "alertas"
    assert dados["total_itens"] == len(dados["itens"]) >= 1
    assert "Bruno Costa" in {i["aluno_nome"] for i in dados["itens"]}
    assert "alerta(s) pendentes" in dados["texto"]


def test_alertas_filtra_pelo_tipo_citado(api):
    dados = perguntar(api, "alertas de frequência")

    assert dados["total_itens"] >= 1
    assert all("Frequência" in i["detalhe"] for i in dados["itens"])


def test_responde_a_projecao_com_as_regras_padrao(api):
    dados = perguntar(api, "quantos alunos podem ficar em recuperação?")

    assert dados["intencao"] == "projecao"
    assert "regras padrão" in dados["texto"]
    assert "Retenção projetada" in dados["texto"]
    assert all(i["detalhe"] for i in dados["itens"])


def test_desistencia_continua_fora_do_escopo(api):
    dados = perguntar(api, "quantos desistiram?")

    assert dados["intencao"] == "fora_do_escopo"


# ---------- Contrato e permissões ----------


@pytest.mark.parametrize("pergunta", ["", "a", "x" * 301])
def test_pergunta_com_tamanho_invalido_e_422(api, pergunta):
    resposta = api["http"].post("/copiloto/perguntas", json={"pergunta": pergunta})

    assert resposta.status_code == 422


def test_campo_extra_e_recusado(api):
    resposta = api["http"].post("/copiloto/perguntas", json={"pergunta": "resumo", "x": 1})

    assert resposta.status_code == 422


def test_so_gestao_usa_o_copiloto(api):
    api["papel"] = "professor"

    assert api["http"].post("/copiloto/perguntas", json={"pergunta": "resumo"}).status_code == 403
    assert api["http"].get("/copiloto/sugestoes").status_code == 403


def test_sugestoes(api):
    sugestoes = api["http"].get("/copiloto/sugestoes").json()["dados"]

    assert len(sugestoes) == 6


def test_pergunta_com_html_nao_e_repetida_como_html(api):
    dados = perguntar(api, "<script>alert(1)</script> resumo")

    # O texto da pergunta nunca volta na resposta, exceto o termo desconhecido já normalizado.
    assert "<script>" not in str(dados)
