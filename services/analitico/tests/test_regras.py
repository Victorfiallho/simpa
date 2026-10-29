"""Regras de média, frequência e risco, com valores calculados à mão (RF07, D04–D09)."""

from decimal import Decimal as D

import pytest

from app.services.regras import (
    classificar,
    consolidar,
    media_ponderada,
    percentual_de_frequencia,
)


def test_media_ponderada_pelos_pesos():
    # (6,00 × 4 + 8,00 × 6) / 10 = 7,20
    assert media_ponderada([(D("6.00"), D("4")), (D("8.00"), D("6"))]) == D("7.20")


def test_media_sem_notas_e_nula():
    assert media_ponderada([]) is None


def test_frequencia_derivada_com_half_up():
    # 25 presenças em 32 aulas = 78,125% → 78,13
    assert percentual_de_frequencia(32, 7) == D("78.13")
    assert percentual_de_frequencia(0, 0) is None


@pytest.mark.parametrize(
    ("notas", "media_esperada", "status_esperado"),
    [
        # (5,97 × 2 + 6,00 × 8) / 10 = 5,994 → 5,99 → Em risco
        ([("5.97", "2"), ("6.00", "8")], "5.99", "em_risco"),
        # (5,95 × 1 + 6,00 × 9) / 10 = 5,995 → 6,00 → Sem risco
        ([("5.95", "1"), ("6.00", "9")], "6.00", "sem_risco"),
    ],
    ids=["5,994-em-risco", "5,995-sem-risco"],
)
def test_fronteira_arredonda_antes_de_classificar(notas, media_esperada, status_esperado):
    """D06: o valor exibido é exatamente o valor usado na decisão."""
    media = media_ponderada([(D(n), D(p)) for n, p in notas])

    assert media == D(media_esperada)
    assert classificar("EST", media, D("90.00")).status == status_esperado


def test_rf07_ca01_media_baixa_e_risco():
    resultado = classificar("POO", D("4.50"), D("90.00"))

    assert resultado.status == "em_risco"
    assert resultado.criterios == ("media_baixa",)
    assert resultado.justificativa == "POO: média 4,50 (< 6,00) — media_baixa"


def test_rf07_ca02_frequencia_baixa_e_risco():
    resultado = classificar("POO", D("8.00"), D("70.00"))

    assert resultado.status == "em_risco"
    assert resultado.criterios == ("frequencia_baixa",)
    assert "frequência 70,00% (< 75,00%)" in resultado.justificativa


def test_rf07_ca03_criterios_atendidos_e_sem_risco():
    resultado = classificar("POO", D("8.00"), D("90.00"))

    assert resultado.status == "sem_risco"
    assert resultado.atencao is False
    assert resultado.criterios == ()


def test_os_dois_criterios_aparecem_na_justificativa():
    resultado = classificar("ALG", D("4.00"), D("60.00"))

    assert resultado.criterios == ("media_baixa", "frequencia_baixa")


def test_fronteira_exata_e_sem_risco_com_atencao():
    """6,00 e 75,00% atendem o mínimo, mas ficam na faixa de atenção (D08)."""
    resultado = classificar("EST", D("6.00"), D("75.00"))

    assert resultado.status == "sem_risco"
    assert resultado.atencao is True
    assert resultado.situacao == "atencao"


@pytest.mark.parametrize(
    ("media", "frequencia", "atencao"),
    [("6.99", "95.00", True), ("7.00", "79.99", True), ("7.00", "80.00", False)],
)
def test_faixa_de_atencao(media, frequencia, atencao):
    assert classificar("EST", D(media), D(frequencia)).atencao is atencao


def test_sem_dados_e_indeterminado():
    resultado = classificar("EST", None, D("90.00"))

    assert resultado.status == "indeterminado"
    assert resultado.justificativa == "EST: sem notas lançadas — dados_insuficientes"


def test_aluno_em_risco_se_qualquer_disciplina_estiver_em_risco():
    """D04: o risco é por inscrição; uma disciplina basta."""
    status, _ = consolidar(
        [
            classificar("EST", D("9.00"), D("95.00")),
            classificar("ALG", D("4.00"), D("95.00")),
        ]
    )
    assert status == "em_risco"


def test_disciplina_sem_dados_nao_esconde_as_outras():
    """D09/D19: inscrição sem dados não conta; o aluno fica com o resultado das outras."""
    status, atencao = consolidar(
        [classificar("EST", None, None), classificar("ALG", D("6.50"), D("95.00"))]
    )
    assert (status, atencao) == ("sem_risco", True)


def test_aluno_sem_nenhum_dado_e_indeterminado():
    assert consolidar([classificar("EST", None, None)]) == ("indeterminado", False)
