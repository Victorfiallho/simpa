"""Inscrições, notas e frequências: regras do RF03, D01, D02, D10 e os eventos (D14)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.main import app
from app.models import Aluno


def nota(cliente, inscricao, valor="7.50", periodo="N1", peso="4"):
    return cliente.post(
        "/avaliacoes",
        json={
            "inscricao_id": inscricao["id"],
            "tipo_avaliacao": "prova",
            "periodo_avaliacao": periodo,
            "nota": valor,
            "peso": peso,
        },
    )


def frequencia(cliente, inscricao, faltas=4, aulas=32, periodo="N1"):
    return cliente.post(
        "/frequencias",
        json={
            "inscricao_id": inscricao["id"],
            "periodo_avaliacao": periodo,
            "aulas_previstas": aulas,
            "faltas": faltas,
        },
    )


def test_inscricao_unica_por_aluno_e_disciplina(cliente, inscricao):
    resposta = cliente.post(
        "/inscricoes",
        json={"aluno_id": inscricao["aluno_id"], "disciplina_id": inscricao["disciplina_id"]},
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "INSCRICAO_DUPLICADA"


def test_aluno_inativo_nao_pode_se_inscrever(cliente, aluno, disciplina):
    cliente.delete(f"/alunos/{aluno['id']}")

    resposta = cliente.post(
        "/inscricoes", json={"aluno_id": aluno["id"], "disciplina_id": disciplina["id"]}
    )

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "ALUNO_INATIVO"


def test_nota_lancada_com_duas_casas(cliente, inscricao):
    resposta = nota(cliente, inscricao, "5.75")

    assert resposta.status_code == 201
    assert resposta.json()["dados"]["nota"] == "5.75"


def test_nota_fora_de_0_a_10_e_recusada(cliente, inscricao):
    assert nota(cliente, inscricao, "10.01").status_code == 422
    assert nota(cliente, inscricao, "-1").status_code == 422


def test_nota_com_tres_casas_e_recusada(cliente, inscricao):
    resposta = nota(cliente, inscricao, "5.995")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["campos"][0]["regra"] == "decimal_max_places"


def test_percentual_de_frequencia_e_derivado_com_half_up(cliente, inscricao):
    # 25 presenças em 32 aulas = 78,125% → 78,13 (D06)
    resposta = frequencia(cliente, inscricao, faltas=7, aulas=32)

    assert resposta.json()["dados"]["frequencia_percentual"] == "78.13"


def test_percentual_nao_e_aceito_na_entrada(cliente, inscricao):
    resposta = cliente.post(
        "/frequencias",
        json={
            "inscricao_id": inscricao["id"],
            "periodo_avaliacao": "N1",
            "aulas_previstas": 32,
            "faltas": 2,
            "frequencia_percentual": 100,
        },
    )

    assert resposta.status_code == 422


def test_faltas_nao_passam_das_aulas(cliente, inscricao):
    assert frequencia(cliente, inscricao, faltas=33, aulas=32).status_code == 422

    criada = frequencia(cliente, inscricao, faltas=2, aulas=32).json()["dados"]
    resposta = cliente.patch(f"/frequencias/{criada['id']}", json={"aulas_previstas": 1})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "FALTAS_INVALIDAS"


def test_uma_frequencia_por_periodo(cliente, inscricao):
    frequencia(cliente, inscricao, periodo="N1")
    resposta = frequencia(cliente, inscricao, periodo="N1")

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "FREQUENCIA_DUPLICADA"


def test_disciplina_encerrada_bloqueia_lancamentos(cliente, inscricao, disciplina):
    lancada = nota(cliente, inscricao).json()["dados"]
    cliente.patch(f"/disciplinas/{disciplina['id']}", json={"status": "encerrada"})

    for resposta in (
        nota(cliente, inscricao),
        frequencia(cliente, inscricao),
        cliente.patch(f"/avaliacoes/{lancada['id']}", json={"nota": "9.00"}),
        cliente.delete(f"/avaliacoes/{lancada['id']}"),
        cliente.delete(f"/inscricoes/{inscricao['id']}"),
    ):
        assert resposta.status_code == 409
        assert resposta.json()["erro"]["codigo"] == "DISCIPLINA_ENCERRADA"


def test_encerrar_a_turma_bloqueia_as_disciplinas(cliente, inscricao, turma):
    cliente.patch(f"/turmas/{turma['id']}", json={"status": "encerrada"})

    resposta = nota(cliente, inscricao)

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "DISCIPLINA_ENCERRADA"


def test_inscricao_trancada_nao_recebe_nota(cliente, inscricao):
    cliente.patch(f"/inscricoes/{inscricao['id']}", json={"status": "trancada"})

    resposta = nota(cliente, inscricao)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "INSCRICAO_INATIVA"


def test_delete_de_inscricao_e_logico(cliente, inscricao):
    resposta = cliente.delete(f"/inscricoes/{inscricao['id']}")

    assert resposta.json()["dados"]["status"] == "cancelada"


def test_cada_alteracao_publica_um_evento(cliente, inscricao, eventos):
    avaliacao = nota(cliente, inscricao).json()["dados"]
    cliente.patch(f"/avaliacoes/{avaliacao['id']}", json={"nota": "8.00"})
    frequencia(cliente, inscricao)
    cliente.delete(f"/avaliacoes/{avaliacao['id']}")

    assert [c for c, _ in eventos] == [
        "inscricao.alterada",
        "avaliacao.alterada",
        "avaliacao.alterada",
        "frequencia.alterada",
        "avaliacao.alterada",
    ]
    assert all(dados == {"inscricao_id": inscricao["id"]} for _, dados in eventos)


def test_erro_de_validacao_nao_publica_evento(cliente, inscricao, eventos):
    eventos.clear()
    nota(cliente, inscricao, "11")

    assert eventos == []


def test_consulta_integrada_do_aluno(cliente, aluno, inscricao):
    nota(cliente, inscricao, "6.00", "N1", "4")
    nota(cliente, inscricao, "8.00", "N2", "6")
    frequencia(cliente, inscricao, faltas=8, aulas=32)

    por_id = cliente.get(f"/alunos/{aluno['id']}").json()["dados"]
    por_matricula = cliente.get(f"/alunos/matricula/{aluno['matricula']}").json()["dados"]

    assert por_id == por_matricula
    detalhe = por_id["inscricoes"][0]
    assert detalhe["disciplina"]["nome"] == "Estatística Aplicada"
    assert [a["nota"] for a in detalhe["avaliacoes"]] == ["6.00", "8.00"]
    assert detalhe["frequencias"][0]["frequencia_percentual"] == "75.00"


def test_rota_interna_entrega_a_inscricao_completa(cliente, inscricao):
    nota(cliente, inscricao)

    corpo = cliente.get(f"/internal/inscricoes/{inscricao['id']}").json()["dados"]

    assert corpo["id"] == inscricao["id"]
    assert len(corpo["avaliacoes"]) == 1


def test_banco_bloqueia_exclusao_fisica_com_historico(cliente, inscricao):
    """ON DELETE RESTRICT: o banco não deixa apagar um aluno que tem inscrições."""
    db = next(app.dependency_overrides[get_db]())
    db.delete(db.get(Aluno, inscricao["aluno_id"]))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_nao_cria_disciplina_em_turma_encerrada(cliente, turma):
    cliente.patch(f"/turmas/{turma['id']}", json={"status": "encerrada"})

    resposta = cliente.post(
        "/disciplinas",
        json={
            "nome": "POO",
            "carga_horaria": 60,
            "periodo_letivo": "2026.2",
            "turma_id": turma["id"],
        },
    )

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["codigo"] == "TURMA_ENCERRADA"
