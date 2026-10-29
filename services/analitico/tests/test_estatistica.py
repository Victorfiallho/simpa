"""Estatística descritiva com valores calculados à mão (RF05, D07)."""

from decimal import Decimal as D

from app.services.estatistica import correlacao, histograma, resumir

NOTAS = [D("6"), D("7"), D("8"), D("9")]


def test_resumo_populacional():
    # média 7,5; desvios² = 2,25 + 0,25 + 0,25 + 2,25 = 5; variância 5/4 = 1,25
    resumo = resumir(NOTAS, amostral=False)

    assert resumo.n == 4
    assert resumo.media == D("7.50")
    assert resumo.mediana == D("7.50")
    assert resumo.variancia == D("1.25")
    assert resumo.desvio_padrao == D("1.12")  # √1,25 = 1,118...
    assert (resumo.minimo, resumo.maximo) == (D("6"), D("9"))
    assert resumo.tipo_variancia == "populacional"


def test_resumo_amostral_divide_por_n_menos_1():
    # 5/3 = 1,666... → 1,67; √1,666... = 1,290... → 1,29
    resumo = resumir(NOTAS, amostral=True)

    assert resumo.variancia == D("1.67")
    assert resumo.desvio_padrao == D("1.29")
    assert resumo.tipo_variancia == "amostral"


def test_mediana_com_quantidade_impar():
    assert resumir([D("9"), D("5"), D("7")], amostral=False).mediana == D("7.00")


def test_amostra_insuficiente():
    resumo = resumir([D("7")], amostral=True)

    assert resumo.variancia is None
    assert resumo.desvio_padrao is None
    assert resumo.observacao == "amostra insuficiente"


def test_um_valor_no_universo_completo_tem_variancia_zero():
    assert resumir([D("7")], amostral=False).variancia == D("0.00")


def test_sem_valores():
    resumo = resumir([], amostral=False)

    assert resumo.n == 0
    assert resumo.media is None
    assert resumo.observacao == "sem dados"


def test_histograma_inclui_o_10_na_ultima_faixa():
    assert histograma([D("0"), D("5.99"), D("6"), D("9.5"), D("10")]) == [
        1, 0, 0, 0, 0, 1, 1, 0, 0, 2,
    ]  # fmt: skip


def test_correlacao_perfeita_e_inversa():
    xs = [D("70"), D("80"), D("90")]

    assert correlacao(xs, [D("5"), D("6"), D("7")]) == D("1.00")
    assert correlacao(xs, [D("7"), D("6"), D("5")]) == D("-1.00")


def test_correlacao_sem_variacao_e_nula():
    assert correlacao([D("80"), D("80")], [D("5"), D("7")]) is None
