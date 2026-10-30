"""Registro semanal de presença e atividades (RF07): base do sinal de abandono silencioso."""

import pytest

SEGUNDA = "2026-09-07"  # uma segunda-feira


def registro(inscricao, **alteracoes):
    return {
        "inscricao_id": inscricao["id"],
        "semana_inicio": SEGUNDA,
        "presente": True,
        "atividades_previstas": 2,
        "atividades_entregues": 1,
    } | alteracoes


def test_lanca_uma_semana(cliente, inscricao):
    resposta = cliente.post("/semanas", json=registro(inscricao))

    assert resposta.status_code == 201
    dados = resposta.json()["dados"]
    assert (dados["semana_inicio"], dados["presente"], dados["atividades_entregues"]) == (
        SEGUNDA,
        True,
        1,
    )


def test_semana_deve_comecar_na_segunda(cliente, inscricao):
    resposta = cliente.post("/semanas", json=registro(inscricao, semana_inicio="2026-09-08"))

    assert resposta.status_code == 422


def test_semana_repetida_e_409(cliente, inscricao):
    cliente.post("/semanas", json=registro(inscricao))

    repetida = cliente.post("/semanas", json=registro(inscricao, presente=False))

    assert repetida.status_code == 409
    assert repetida.json()["erro"]["codigo"] == "SEMANA_DUPLICADA"


@pytest.mark.parametrize(
    "alteracao",
    [
        {"atividades_entregues": 3},  # mais entregues que previstas
        {"atividades_previstas": -1},
        {"atividades_previstas": 51},
        {"presente": "talvez"},
        {"campo_extra": 1},
    ],
)
def test_dados_invalidos_sao_422(cliente, inscricao, alteracao):
    assert cliente.post("/semanas", json=registro(inscricao, **alteracao)).status_code == 422


def test_inscricao_inexistente_e_422(cliente):
    resposta = cliente.post("/semanas", json=registro({"id": 999}))

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "REFERENCIA_INVALIDA"


def test_atualiza_a_semana(cliente, inscricao):
    criada = cliente.post("/semanas", json=registro(inscricao)).json()["dados"]

    resposta = cliente.patch(
        f"/semanas/{criada['id']}", json={"presente": False, "atividades_entregues": 0}
    )

    dados = resposta.json()["dados"]
    assert (dados["presente"], dados["atividades_entregues"]) == (False, 0)


def test_atualizar_nao_deixa_entregues_passarem_das_previstas(cliente, inscricao):
    criada = cliente.post("/semanas", json=registro(inscricao)).json()["dados"]

    resposta = cliente.patch(f"/semanas/{criada['id']}", json={"atividades_entregues": 5})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ENTREGAS_INVALIDAS"


def test_remove_a_semana(cliente, inscricao):
    criada = cliente.post("/semanas", json=registro(inscricao)).json()["dados"]

    assert cliente.delete(f"/semanas/{criada['id']}").status_code == 200
    assert cliente.get(f"/semanas/{criada['id']}").status_code == 404


def test_lista_por_inscricao(cliente, inscricao):
    cliente.post("/semanas", json=registro(inscricao))
    cliente.post("/semanas", json=registro(inscricao, semana_inicio="2026-09-14"))

    corpo = cliente.get("/semanas", params={"inscricao_id": inscricao["id"]}).json()

    assert corpo["total_registros"] == 2


def test_disciplina_encerrada_bloqueia_o_registro(cliente, inscricao, disciplina):
    cliente.patch(f"/disciplinas/{disciplina['id']}", json={"status": "encerrada"})

    resposta = cliente.post("/semanas", json=registro(inscricao))

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "DISCIPLINA_ENCERRADA"


def test_rota_interna_entrega_as_semanas_em_ordem(cliente, inscricao):
    cliente.post("/semanas", json=registro(inscricao, semana_inicio="2026-09-14"))
    cliente.post("/semanas", json=registro(inscricao))

    corpo = cliente.get(f"/internal/inscricoes/{inscricao['id']}").json()["dados"]

    assert [s["semana_inicio"] for s in corpo["semanas"]] == ["2026-09-07", "2026-09-14"]
    assert corpo["semanas"][0]["presente"] is True


# ---------- Perfis (D03): como as notas, só admin e o professor da disciplina lançam ----------


def test_coordenador_nao_lanca_semana(cliente, usuario, inscricao):
    usuario.role = "coordenador"

    resposta = cliente.post("/semanas", json=registro(inscricao))

    assert resposta.status_code == 403


def test_professor_da_disciplina_lanca_e_o_de_fora_nao(cliente, usuario, inscricao):
    usuario.role, usuario.id = "professor", 3
    criada = cliente.post("/semanas", json=registro(inscricao))
    assert criada.status_code == 201

    usuario.id = 99
    assert (
        cliente.post("/semanas", json=registro(inscricao, semana_inicio="2026-09-14")).status_code
        == 403
    )
    registro_id = criada.json()["dados"]["id"]
    assert cliente.patch(f"/semanas/{registro_id}", json={"presente": False}).status_code == 403
    assert cliente.delete(f"/semanas/{registro_id}").status_code == 403
    assert cliente.get(f"/semanas/{registro_id}").status_code == 403
    assert cliente.get("/semanas").json()["total_registros"] == 0
