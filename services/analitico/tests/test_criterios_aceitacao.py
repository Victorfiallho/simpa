"""Critérios de aceitação do SRS (seção 6) que ainda não tinham teste com o próprio nome.

O nome de cada teste diz o requisito e o critério: `test_rf05_ca01_...` é o 1º critério do RF05.
Os dados vêm de tests/test_painel.py, com o acadêmico simulado.
"""

import io
import re

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.clientes import academico
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from app.services import relatorios
from tests.test_painel import INSCRICOES

DUAS_CASAS = re.compile(r"^\d+\.\d{2}$")


def _filtrar(aluno_id=None, disciplina_id=None, turma_id=None, periodo_letivo=None):
    """O que a rota /internal do acadêmico faria com cada filtro."""
    return [
        i
        for i in INSCRICOES
        if (aluno_id is None or i.aluno.id == aluno_id)
        and (disciplina_id is None or i.disciplina.id == disciplina_id)
        and (turma_id is None or i.disciplina.turma_id == turma_id)
        and (periodo_letivo is None or i.disciplina.periodo_letivo == periodo_letivo)
    ]


@pytest.fixture
def chamadas(monkeypatch):
    """Filtros com que cada rota consultou o acadêmico."""
    registradas: list[dict] = []

    def buscar(**filtros):
        registradas.append(filtros)
        return _filtrar(**filtros)

    monkeypatch.setattr(academico, "buscar_inscricoes", buscar)
    return registradas


@pytest.fixture
def cliente(chamadas):
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(
        id=1, role="coordenador", nome="coordenacao"
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- RF05: indicadores estatísticos ----------

INDICADORES = {"media", "mediana", "variancia", "desvio_padrao", "minimo", "maximo"}


@pytest.mark.parametrize(
    ("rota", "validas"),
    [
        ("/indicadores/alunos/1", 2),  # Ana: Estatística e Álgebra
        ("/indicadores/disciplinas/1", 2),  # Estatística: Ana e Bruno (Clara sem dados)
        ("/indicadores/turmas/1", 4),
        ("/indicadores/periodos/2026.2", 4),
    ],
)
def test_rf05_ca01_indicadores_em_cada_nivel_de_agregacao(cliente, rota, validas):
    resposta = cliente.get(rota)

    assert resposta.status_code == 200
    dados = resposta.json()["dados"]
    assert dados["inscricoes_validas"] == validas
    assert INDICADORES <= set(dados["media"])
    assert dados["frequencia"]["media"] is not None


def test_rf05_ca02_media_ponderada_com_duas_casas(cliente):
    dados = cliente.get("/indicadores/alunos/1").json()["dados"]

    # Estatística: 8,00 × 4 + 9,00 × 6 → 8,60. Álgebra: 4,00 × 4 + 5,00 × 6 → 4,60.
    assert dados["media"]["maximo"] == "8.60"
    assert dados["media"]["minimo"] == "4.60"
    assert dados["media"]["media"] == "6.60"
    for chave in ("media", "mediana", "minimo", "maximo", "desvio_padrao"):
        assert DUAS_CASAS.match(dados["media"][chave]), (chave, dados["media"][chave])


# ---------- RF11: relatórios ----------


def test_rf11_ca01_relatorio_repassa_os_filtros_e_os_registra(cliente, chamadas):
    texto = cliente.get(
        "/relatorios/inscricoes",
        params={"formato": "csv", "turma_id": 1, "disciplina_id": 3, "periodo_letivo": "2026.2"},
    ).content.decode("utf-8-sig")

    assert chamadas == [{"turma_id": 1, "disciplina_id": 3, "periodo_letivo": "2026.2"}]
    assert "Filtros;turma = 1, disciplina = 3, período = 2026.2" in texto
    linhas_de_dados = [linha for linha in texto.splitlines() if "@aluno.simpa.dev" in linha]
    assert linhas_de_dados and all("Álgebra" in linha for linha in linhas_de_dados)


def test_rf11_ca03_xlsx_identifica_data_hora_e_usuario(cliente):
    resposta = cliente.get("/relatorios/inscricoes", params={"formato": "xlsx"})

    planilha = load_workbook(io.BytesIO(resposta.content)).active
    linhas = {linha[0]: linha[1] for linha in planilha.iter_rows(max_row=5, values_only=True)}
    assert re.match(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2} ", linhas["Gerado em"])
    assert linhas["Gerado por"] == "coordenacao (coordenador)"


def test_rf11_ca03_pdf_identifica_data_hora_e_usuario(cliente, monkeypatch):
    # O texto do PDF sai comprimido; o que se confere é o parágrafo que o gerador escreve nele.
    escritos: list[str] = []
    original = relatorios.Paragraph

    def paragrafo(texto, *args, **kwargs):
        escritos.append(texto)
        return original(texto, *args, **kwargs)

    monkeypatch.setattr(relatorios, "Paragraph", paragrafo)

    resposta = cliente.get("/relatorios/inscricoes", params={"formato": "pdf"})

    assert resposta.content.startswith(b"%PDF")
    assert any(
        re.search(r"Gerado em \d{2}/\d{2}/\d{4} \d{2}:\d{2} .* por coordenacao \(coordenador\)", t)
        for t in escritos
    )
