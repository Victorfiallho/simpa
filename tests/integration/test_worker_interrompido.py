"""Interrupção do worker do analítico (etapa 4.4 do plano de qualidade).

Com o worker parado, o acadêmico continua gravando e a mensagem fica na fila. Quando o worker
volta, o histórico se atualiza sem novo lançamento. Este teste derruba um serviço do ambiente
compartilhado: não rode outros testes em paralelo com ele (marcador `interrupcao`).
"""

from __future__ import annotations

import pytest

from tests.integration import suporte
from tests.integration.suporte import dados, esperar_ate

FILA = "analitico.recalculo-risco"
FALHAS = "analitico.recalculo-risco.falhas"


def _fila(nome: str) -> dict[str, int]:
    return suporte.filas().get(nome, {"mensagens": -1, "consumidores": -1})


@pytest.mark.interrupcao
def test_evento_espera_o_worker_parado_e_chega_quando_ele_volta(admin, prof_ana):
    turma = suporte.criar_turma(admin)
    disciplina = suporte.criar_disciplina(admin, turma["id"], prof_ana.usuario_id)
    aluno = suporte.criar_aluno(admin, turma["id"])
    inscricao = suporte.inscrever(admin, aluno["id"], disciplina["id"])
    nota = suporte.lancar_nota(admin, inscricao["id"], "8.00")
    suporte.lancar_frequencia(admin, inscricao["id"], faltas=1)
    esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == "sem_risco",
        "situação inicial sem risco (o fluxo está saudável antes da interrupção)",
    )
    falhas_antes = _fila(FALHAS)["mensagens"]

    try:
        suporte.compose("stop", "analitico-worker", timeout=60)
        esperar_ate(lambda: _fila(FILA)["consumidores"], lambda n: n == 0, "fila sem consumidor")

        # O acadêmico não depende do worker: a nota é gravada e devolvida normalmente.
        dados(admin.patch(f"/academico/avaliacoes/{nota['id']}", {"nota": "4.00"}))
        assert dados(admin.get(f"/academico/avaliacoes/{nota['id']}"))["nota"] == "4.00"

        # A mensagem fica pendente na fila e o histórico ainda não mudou.
        esperar_ate(lambda: _fila(FILA)["mensagens"], lambda n: n >= 1, "mensagem pendente na fila")
        assert suporte.estados(suporte.historico(admin, inscricao["id"]))[-1] == "sem_risco"
    finally:
        # Religa mesmo se uma asserção acima falhar, e só segue com o worker saudável.
        suporte.compose(
            "up",
            "-d",
            "--no-build",
            "--wait",
            "--wait-timeout",
            "90",
            "analitico-worker",
            timeout=120,
        )

    historico = esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == "em_risco",
        "histórico atualizado depois que o worker voltou, sem novo lançamento",
    )
    assert suporte.estados(historico)[-2:] == ["sem_risco", "em_risco"]
    esperar_ate(lambda: _fila(FILA)["mensagens"], lambda n: n == 0, "fila drenada")
    assert _fila(FALHAS)["mensagens"] == falhas_antes, (
        "a interrupção não pode gerar mensagens na fila de falhas"
    )
