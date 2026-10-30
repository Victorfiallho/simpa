"""Abandono silencioso (RF07): ausência seguida e quase nenhuma atividade entregue."""

from datetime import date, timedelta

import pytest

from app.clientes import academico
from app.services.abandono import (
    semanas_seguidas_ausente,
    sinal_da_disciplina,
    sinal_do_aluno,
)
from tests.test_alertas import estado  # noqa: F401  (acadêmico e banco simulados)
from tests.test_painel import BOM, inscricao

SEGUNDA = date(2026, 8, 3)
SUMIDA = [(False, 2, 0), (False, 2, 0), (False, 2, 0)]
BEM = [(True, 2, 2), (True, 2, 2), (True, 2, 2)]


def semanas(registros):
    """Cada registro: (presente, previstas, entregues), uma semana após a outra."""
    return [
        academico.Semana(
            semana_inicio=SEGUNDA + timedelta(weeks=i),
            presente=presente,
            atividades_previstas=previstas,
            atividades_entregues=entregues,
        )
        for i, (presente, previstas, entregues) in enumerate(registros)
    ]


def com_semanas(id_, aluno_id, nome, sigla, registros):
    base = inscricao(id_, aluno_id, nome, sigla, BOM)
    base.semanas = semanas(registros)
    return base


# ---------- Por disciplina ----------


def test_conta_semanas_ausentes_seguidas_do_fim():
    ins = com_semanas(
        1, 1, "Ana", "EST", [(True, 2, 2), (False, 2, 1), (False, 2, 0), (False, 2, 0)]
    )

    assert semanas_seguidas_ausente(ins) == 3


def test_presenca_na_ultima_semana_zera_a_contagem():
    ins = com_semanas(1, 1, "Ana", "EST", [(False, 2, 0), (False, 2, 0), (True, 2, 0)])

    assert semanas_seguidas_ausente(ins) == 0


def test_so_as_seis_ultimas_semanas_contam():
    ins = com_semanas(1, 1, "Ana", "EST", [(False, 1, 0)] * 10)

    assert semanas_seguidas_ausente(ins) == 6


def test_sem_registro_nao_ha_sinal():
    assert sinal_da_disciplina(inscricao(1, 1, "Ana", "EST", BOM)) is None


@pytest.mark.parametrize(
    ("registros", "nivel"),
    [
        # 3 semanas ausente, nada entregue, 2+ previstas: alto
        ([(True, 2, 0), (False, 1, 0), (False, 1, 0), (False, 1, 0)], "alto"),
        # 2 semanas ausente e nada entregue: atenção
        ([(True, 2, 0), (True, 2, 0), (False, 2, 0), (False, 2, 0)], "atencao"),
        # 3 semanas ausente, entregou 1 de 4 (25%): atenção, não alto
        ([(True, 1, 0), (False, 1, 0), (False, 1, 0), (False, 1, 1)], "atencao"),
        # ausente 3 semanas, mas entregou quase tudo: sem sinal
        ([(False, 1, 1), (False, 1, 1), (False, 1, 1)], None),
        # só 1 semana ausente: sem sinal
        ([(True, 2, 0), (False, 2, 0)], None),
        # ausente 3 semanas, mas nenhuma atividade prevista: sem sinal
        ([(False, 0, 0), (False, 0, 0), (False, 0, 0)], None),
    ],
)
def test_nivel_do_sinal_por_disciplina(registros, nivel):
    sinal = sinal_da_disciplina(com_semanas(1, 1, "Ana", "EST", registros))

    assert (sinal.nivel if sinal else None) == nivel


def test_atividades_olham_so_as_quatro_ultimas_semanas():
    # As 2 primeiras semanas (6 entregues) ficam fora; nas 4 últimas entregou 0 de 4.
    registros = [(True, 3, 3), (True, 3, 3)] + [(False, 1, 0)] * 4
    sinal = sinal_da_disciplina(com_semanas(1, 1, "Ana", "EST", registros))

    assert (sinal.previstas, sinal.entregues, sinal.ausencia) == (4, 0, 4)


# ---------- Do aluno ----------


def test_metade_das_disciplinas_com_o_sinal_gera_alerta():
    ana = [
        com_semanas(1, 1, "Ana Lima", "EST", SUMIDA),
        com_semanas(2, 1, "Ana Lima", "ALG", BEM),
    ]

    sinal = sinal_do_aluno(ana)

    assert sinal.tipo == "abandono"
    assert sinal.nivel == "alto"
    assert sinal.titulo == "Ausente há 3 semana(s) seguidas e quase sem entregar atividades"
    assert sinal.detalhe.startswith("1 de 2 disciplina(s) com o sinal (EST)")
    assert "0 de 6 atividade(s) entregue(s) nas últimas 4 semanas" in sinal.detalhe


def test_menos_da_metade_das_disciplinas_nao_gera_alerta():
    tres = [
        com_semanas(1, 1, "Ana", "EST", SUMIDA),
        com_semanas(2, 1, "Ana", "ALG", BEM),
        com_semanas(3, 1, "Ana", "POO", BEM),
    ]

    assert sinal_do_aluno(tres) is None


def test_gravidade_do_aluno_so_e_alta_se_metade_das_marcadas_for_alta():
    alto = [(False, 1, 0), (False, 1, 0), (False, 2, 0)]
    leve = [(True, 2, 0), (False, 2, 0), (False, 2, 0)]
    duas = [com_semanas(1, 1, "Ana", "EST", alto), com_semanas(2, 1, "Ana", "ALG", leve)]
    # 2 disciplinas marcadas, 1 grave: ceil(2 / 2) = 1, então o alerta é alto
    assert sinal_do_aluno(duas).nivel == "alto"

    so_leves = [com_semanas(1, 1, "Ana", "EST", leve), com_semanas(2, 1, "Ana", "ALG", leve)]
    assert sinal_do_aluno(so_leves).nivel == "atencao"


def test_aluno_sem_dados_nao_gera_alerta():
    sem_dados = inscricao(1, 1, "Ana", "EST")  # sem notas nem frequência
    sem_dados.semanas = semanas(SUMIDA)

    assert sinal_do_aluno([sem_dados]) is None


# ---------- Nas rotas de alertas ----------


def sumido():
    registros = [(True, 2, 0), (False, 2, 0), (False, 2, 0), (False, 2, 0)]
    return com_semanas(1, 7, "Davi Reis", "EST", registros)


def alertas(estado, **params):  # noqa: F811
    return estado["cliente"].get("/alertas", params=params).json()["dados"]


def test_alerta_de_abandono_aparece_na_lista(estado):  # noqa: F811
    estado["inscricoes"] = [sumido()]

    dados = alertas(estado)

    abandono = [a for a in dados["alertas"] if a["tipo"] == "abandono"]
    assert len(abandono) == 1
    assert abandono[0]["disciplina_id"] == 0
    assert abandono[0]["disciplina_nome"] == "Todas as disciplinas"
    assert abandono[0]["nivel"] == "alto"
    assert abandono[0]["professor_id"] is None
    assert [r["tipo"] for r in dados["resumo"]] == ["queda", "frequencia", "abandono"]


def test_abandono_vem_antes_dos_outros_na_mesma_gravidade(estado):  # noqa: F811
    davi = sumido()
    davi.frequencias[0].faltas = 12  # frequência abaixo de 75%: também alto
    estado["inscricoes"] = [davi]

    tipos = [a["tipo"] for a in alertas(estado)["alertas"]]

    assert tipos[0] == "abandono"
    assert "frequencia" in tipos


def test_muda_o_atendimento_do_abandono(estado):  # noqa: F811
    estado["inscricoes"] = [sumido()]

    resposta = estado["cliente"].put(
        "/alertas/atendimento",
        json={"aluno_id": 7, "tipo": "abandono", "disciplina_id": 0, "estado": "acomp"},
    )

    assert resposta.status_code == 200
    assert alertas(estado, tipo="abandono")["alertas"][0]["estado"] == "acomp"


def test_acompanhar_o_aluno_move_o_abandono_para_em_acompanhamento(estado):  # noqa: F811
    estado["inscricoes"] = [sumido()]

    estado["cliente"].post(
        "/acompanhamentos",
        json={
            "aluno_id": 7,
            "tipo": "contato",
            "data": date.today().isoformat(),
            "observacao": "Liguei e combinei um encontro.",
        },
    )

    assert alertas(estado, tipo="abandono")["alertas"][0]["estado"] == "acomp"


def test_aluno_presente_na_ultima_semana_nao_gera_abandono(estado):  # noqa: F811
    registros = [(False, 2, 0), (False, 2, 0), (False, 2, 0), (True, 2, 1)]
    estado["inscricoes"] = [com_semanas(1, 7, "Davi Reis", "EST", registros)]

    assert alertas(estado, tipo="abandono")["alertas"] == []
