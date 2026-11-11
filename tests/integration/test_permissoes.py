"""Permissões entre serviços (etapa 4.3 do plano de qualidade, D03).

Um aluno inscrito em uma disciplina de cada professor: cada professor enxerga só o que é seu,
em qualquer nível do corpo da resposta. A gestão continua vendo as duas.
"""

from __future__ import annotations

import pytest

from tests.integration import suporte
from tests.integration.suporte import Sessao, dados

TOKEN_EXPIRADO = """
import jwt
from datetime import UTC, datetime, timedelta
from app.core import seguranca as s
agora = datetime.now(UTC)
print(jwt.encode(
    {"sub": "3", "nome": "ana", "role": "professor", "iss": s.EMISSOR,
     "iat": agora - timedelta(hours=2), "exp": agora - timedelta(hours=1)},
    s.chave_privada(), algorithm=s.ALGORITMO, headers={"kid": s.KID},
))
"""


@pytest.fixture
def aluno_compartilhado(admin, prof_ana, prof_bruno):
    """Aluno com uma inscrição na disciplina de Ana (nota 7) e outra na de Bruno (nota 3)."""
    turma = suporte.criar_turma(admin)
    disc_a = suporte.criar_disciplina(admin, turma["id"], prof_ana.usuario_id, "Disciplina da Ana")
    disc_b = suporte.criar_disciplina(
        admin, turma["id"], prof_bruno.usuario_id, "Disciplina do Bruno"
    )
    aluno = suporte.criar_aluno(admin, turma["id"])
    insc_a = suporte.inscrever(admin, aluno["id"], disc_a["id"])
    insc_b = suporte.inscrever(admin, aluno["id"], disc_b["id"])
    nota_a = suporte.lancar_nota(admin, insc_a["id"], "7.00")
    nota_b = suporte.lancar_nota(admin, insc_b["id"], "3.00")
    freq_a = suporte.lancar_frequencia(admin, insc_a["id"], faltas=1)
    freq_b = suporte.lancar_frequencia(admin, insc_b["id"], faltas=9)
    return {
        "aluno": aluno,
        "disciplinas": {"a": disc_a, "b": disc_b},
        "inscricoes": {"a": insc_a, "b": insc_b},
        "notas": {"a": nota_a, "b": nota_b},
        "frequencias": {"a": freq_a, "b": freq_b},
    }


def _rotas_do_aluno(aluno: dict) -> tuple[str, str]:
    return (f"/academico/alunos/{aluno['id']}", f"/academico/alunos/matricula/{aluno['matricula']}")


def _conferir_so(corpo: dict, texto: str, dono: str, outro: str, c: dict) -> None:
    """O corpo cita só a inscrição, a nota e a frequência de `dono`, em qualquer nível."""
    assert [i["id"] for i in corpo["inscricoes"]] == [c["inscricoes"][dono]["id"]]
    assert [a["id"] for i in corpo["inscricoes"] for a in i["avaliacoes"]] == [
        c["notas"][dono]["id"]
    ]
    assert [f["id"] for i in corpo["inscricoes"] for f in i["frequencias"]] == [
        c["frequencias"][dono]["id"]
    ]
    assert c["disciplinas"][outro]["nome"] not in texto
    assert {i["disciplina"]["id"] for i in corpo["inscricoes"]} == {c["disciplinas"][dono]["id"]}


def test_professor_ve_so_a_propria_disciplina_do_aluno_compartilhado(
    aluno_compartilhado, prof_ana, prof_bruno
):
    c = aluno_compartilhado
    for professor, dono, outro in ((prof_ana, "a", "b"), (prof_bruno, "b", "a")):
        for rota in _rotas_do_aluno(c["aluno"]):
            resposta = professor.get(rota)
            _conferir_so(dados(resposta), resposta.text, dono, outro, c)


def test_listagens_do_professor_nao_trazem_a_disciplina_de_outro(aluno_compartilhado, prof_ana):
    c = aluno_compartilhado
    id_b = c["disciplinas"]["b"]["id"]
    for rota in ("/academico/inscricoes", "/academico/avaliacoes", "/academico/frequencias"):
        corpo = prof_ana.get(rota, params={"disciplina_id": id_b}).json()
        assert corpo["total_registros"] == 0 and corpo["dados"] == [], rota
    assert prof_ana.get(f"/academico/disciplinas/{id_b}").status_code == 403
    historico_b = prof_ana.get(
        f"/analitico/riscos/inscricoes/{c['inscricoes']['b']['id']}/historico"
    )
    assert historico_b.status_code == 403


def test_professor_nao_altera_nem_lanca_na_disciplina_de_outro(
    aluno_compartilhado, prof_ana, admin
):
    c = aluno_compartilhado
    alteracao = prof_ana.patch(f"/academico/avaliacoes/{c['notas']['b']['id']}", {"nota": "10.00"})
    assert alteracao.status_code == 403, alteracao.text
    novo = prof_ana.post(
        "/academico/avaliacoes",
        {
            "inscricao_id": c["inscricoes"]["b"]["id"],
            "tipo_avaliacao": "prova",
            "periodo_avaliacao": "N2",
            "nota": "10.00",
            "peso": "6",
        },
    )
    assert novo.status_code == 403, novo.text
    # A nota da disciplina de Bruno continua a original: a recusa não deixou rastro.
    nota_b = dados(admin.get(f"/academico/avaliacoes/{c['notas']['b']['id']}"))
    assert nota_b["nota"] == "3.00"
    assert dados(
        admin.get("/academico/avaliacoes", params={"inscricao_id": c["inscricoes"]["b"]["id"]})
    ) == [nota_b]


def test_gestao_ve_as_duas_disciplinas(aluno_compartilhado, coordenacao, admin):
    c = aluno_compartilhado
    for gestor in (coordenacao, admin):
        for rota in _rotas_do_aluno(c["aluno"]):
            corpo = dados(gestor.get(rota))
            assert {i["id"] for i in corpo["inscricoes"]} == {
                c["inscricoes"]["a"]["id"],
                c["inscricoes"]["b"]["id"],
            }


def test_sem_token_ou_com_token_invalido_a_consulta_e_recusada(aluno_compartilhado, anonimo, http):
    rota = _rotas_do_aluno(aluno_compartilhado["aluno"])[0]
    assert anonimo.get(rota).status_code == 401
    assert Sessao(http, "isto.nao.e-um-token").get(rota).status_code == 401
    assert Sessao(http, "").get(rota).status_code == 401


def test_token_expirado_e_recusado_pelo_servidor(aluno_compartilhado, http):
    """O token é assinado de verdade pelo auth, mas já venceu: quem recusa é a validação do JWT."""
    expirado = suporte.compose("exec", "-T", "auth", "python", "-c", TOKEN_EXPIRADO).stdout.strip()
    assert expirado.count(".") == 2, "o auth não devolveu um JWT"
    rota = _rotas_do_aluno(aluno_compartilhado["aluno"])[0]
    resposta = Sessao(http, expirado).get(rota)
    assert resposta.status_code == 401, resposta.text
