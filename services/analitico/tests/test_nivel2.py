"""Nível 2: regressão (análise matricial), recomendações e interpretação automática."""

from decimal import Decimal as D

import pytest

from app.services import predicao
from app.services.interpretacao import gerar_achados
from app.services.painel import calcular, montar_predicao
from app.services.recomendacoes import recomendar
from tests.test_painel import INSCRICOES, inscricao


def _turma_sintetica(formula):
    """10 inscrições com N1 e frequência variadas e N2 = formula(N1, frequência)."""
    dados = []
    for i in range(10):
        n1 = 4 + i * 0.5
        faltas = i % 5
        frequencia = (32 - faltas) / 32 * 100
        n2 = round(formula(n1, frequencia), 2)
        dados.append(
            inscricao(
                100 + i,
                100 + i,
                f"Aluno {i}",
                "EST",
                [("N1", f"{n1:.2f}", "4"), ("N2", f"{n2:.2f}", "6")],
                faltas=faltas,
            )
        )
    return dados


def test_regressao_recupera_os_coeficientes_de_uma_relacao_exata():
    # N2 = 1 + 0,5·N1 + 0,02·frequência: o modelo tem que achar exatamente isso.
    calculadas = [calcular(i) for i in _turma_sintetica(lambda n1, f: 1 + 0.5 * n1 + 0.02 * f)]

    modelo = predicao.ajustar(calculadas)

    assert modelo is not None
    assert modelo.coeficientes == pytest.approx((1, 0.5, 0.02), abs=0.02)
    assert modelo.r2 == pytest.approx(1, abs=0.001)
    assert modelo.erro_validacao < 0.02


def test_regressao_precisa_de_pelo_menos_8_inscricoes():
    calculadas = [calcular(i) for i in _turma_sintetica(lambda n1, f: n1)[:7]]

    assert predicao.ajustar(calculadas) is None


def test_projecao_da_media_final_usa_os_pesos_da_n1_e_da_n2():
    calculadas = [calcular(i) for i in _turma_sintetica(lambda n1, f: n1 + 1)]
    modelo = predicao.ajustar(calculadas)

    primeira = predicao.prever(modelo, calculadas)[0]

    # N1 = 4,00 (peso 4) e N2 prevista ≈ 5,00 (peso 6) → (16 + 30) / 10 = 4,60
    assert primeira.nota_n2_prevista == pytest.approx(D("5.00"), abs=D("0.05"))
    assert primeira.media_projetada == pytest.approx(D("4.60"), abs=D("0.05"))
    assert primeira.risco_projetado is True


def test_predicao_explica_o_modelo_e_os_limites():
    resultado = montar_predicao(_turma_sintetica(lambda n1, f: 1 + 0.5 * n1 + 0.02 * f))

    assert resultado.modelo.equacao.startswith("N2 = ")
    assert len(resultado.modelo.interpretacao) == 3
    assert len(resultado.previsoes) == 10
    assert resultado.limites


def test_predicao_sem_dados_suficientes_explica_o_motivo():
    resultado = montar_predicao(INSCRICOES)

    assert resultado.modelo is None
    assert "pelo menos 8" in resultado.observacao


# ---------- Recomendações ----------


def _acoes(*inscricoes, projecoes=None):
    return [r.acao for r in recomendar([calcular(i) for i in inscricoes], projecoes or {})]


def test_media_baixa_recomenda_monitoria():
    acoes = _acoes(inscricao(1, 1, "Ana", "ALG", [("N1", "4.00", "4"), ("N2", "5.00", "6")]))

    assert acoes == ["Encaminhar para monitoria ou aulas de reforço em Álgebra"]


def test_frequencia_baixa_recomenda_contato_da_coordenacao():
    acoes = _acoes(
        inscricao(1, 1, "Ana", "POO", [("N1", "8.00", "4"), ("N2", "8.00", "6")], faltas=12)
    )

    assert acoes[0].startswith("Contato da coordenação sobre as faltas em POO")


def test_risco_em_duas_disciplinas_vem_primeiro():
    recomendacoes = recomendar(
        [
            calcular(inscricao(1, 1, "Ana", "ALG", [("N1", "4.00", "4"), ("N2", "4.00", "6")])),
            calcular(inscricao(2, 1, "Ana", "POO", [("N1", "4.00", "4"), ("N2", "4.00", "6")])),
        ],
        {},
    )

    assert recomendacoes[0].acao == "Conversa com a coordenação sobre a carga do semestre"
    assert all(r.prioridade == "alta" for r in recomendacoes)


def test_projecao_de_queda_gera_recomendacao_preventiva():
    sem_risco = inscricao(1, 1, "Ana", "EST", [("N1", "8.00", "4"), ("N2", "8.00", "6")])

    acoes = _acoes(sem_risco, projecoes={1: D("5.50")})

    assert acoes == ["Acompanhar de perto a próxima avaliação de Estatística"]


def test_inscricao_sem_dados_pede_lancamento():
    assert _acoes(inscricao(1, 1, "Ana", "EST"))[0].startswith("Pedir ao professor")


# ---------- Interpretação automática ----------


def test_achados_descrevem_o_risco_e_sua_origem():
    calculadas = [calcular(i) for i in INSCRICOES if i.status == "ativa"]
    achados = gerar_achados(
        calculadas, {"em_risco": 1, "atencao": 1, "sem_risco": 0, "indeterminado": 1}
    )
    por_titulo = {a.titulo: a for a in achados}

    assert por_titulo["Alunos em risco"].gravidade == "alerta"
    assert "1 de 3 alunos (33%)" in por_titulo["Alunos em risco"].texto
    assert "vem principalmente das notas" in por_titulo["Origem do risco"].texto
    assert achados[0].gravidade == "alerta"  # os alertas vêm primeiro


def test_achado_de_tendencia_aponta_a_queda():
    turma = [
        inscricao(i, i, f"Aluno {i}", "EST", [("N1", "8.00", "4"), ("N2", "6.00", "6")])
        for i in range(1, 5)
    ] + [
        inscricao(10 + i, 10 + i, f"Outro {i}", "POO", [("N1", "7.00", "4"), ("N2", "7.00", "6")])
        for i in range(1, 5)
    ]
    achados = gerar_achados([calcular(i) for i in turma], {"sem_risco": 8})

    queda = next(a for a in achados if a.titulo == "Queda de desempenho")
    # Média N1 8,00 → acumulado (8·4 + 6·6)/10 = 6,80: queda de 1,20
    assert "Estatística (turma A) a média caiu 1,20 ponto" in queda.texto


def test_sem_dados_tem_achado_explicativo():
    achados = gerar_achados([calcular(inscricao(1, 1, "Ana", "EST"))], {"indeterminado": 1})

    assert achados[0].titulo == "Sem dados suficientes"
