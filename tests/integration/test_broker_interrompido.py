"""Recuperação do broker e das falhas de processamento (etapa 4.6 do plano de qualidade).

Os testes marcados `interrupcao` derrubam serviços do ambiente compartilhado e os religam no
`finally`, mesmo se uma asserção falhar. Não rode outros testes em paralelo com eles.
"""

from __future__ import annotations

import json

import pytest

from tests.integration import suporte
from tests.integration.suporte import dados, esperar_ate

FILA = "analitico.recalculo-risco"
FALHAS = "analitico.recalculo-risco.falhas"
FALHAS_AUTH = "auth.auditoria.falhas"
ESPERA_5S = "analitico.recalculo-risco.espera.5s"


def _mensagens(fila: str) -> int:
    return suporte.filas().get(fila, {"mensagens": -1})["mensagens"]


def _cenario(admin, prof, nota: str = "8.00"):
    """Inscrição com nota e frequência já refletidas no histórico (fluxo saudável)."""
    situacao = "sem_risco" if float(nota) >= 6 else "em_risco"
    turma = suporte.criar_turma(admin)
    disciplina = suporte.criar_disciplina(admin, turma["id"], prof.usuario_id)
    aluno = suporte.criar_aluno(admin, turma["id"])
    inscricao = suporte.inscrever(admin, aluno["id"], disciplina["id"])
    avaliacao = suporte.lancar_nota(admin, inscricao["id"], nota)
    suporte.lancar_frequencia(admin, inscricao["id"], faltas=1)
    esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == situacao,
        f"situação inicial {situacao}",
    )
    return inscricao, avaliacao


def _religar(*servicos: str) -> None:
    suporte.compose(
        "up", "-d", "--no-build", "--wait", "--wait-timeout", "120", *servicos, timeout=180
    )


@pytest.mark.interrupcao
def test_evento_sobrevive_a_queda_do_broker_e_chega_sem_novo_lancamento(admin, prof_ana):
    inscricao, avaliacao = _cenario(admin, prof_ana)
    falhas_antes = _mensagens(FALHAS)

    try:
        suporte.compose("stop", "rabbitmq", timeout=60)

        # Sem broker, o acadêmico continua gravando e respondendo normalmente.
        corpo = dados(admin.patch(f"/academico/avaliacoes/{avaliacao['id']}", {"nota": "4.00"}))
        assert corpo["nota"] == "4.00"
        assert dados(admin.get(f"/academico/avaliacoes/{avaliacao['id']}"))["nota"] == "4.00"

        # O evento está na outbox, na mesma transação da nota, esperando o broker voltar.
        esperar_ate(
            lambda: suporte.eventos_pendentes(inscricao["id"]),
            lambda n: n >= 1,
            "evento pendente na outbox do acadêmico",
        )
    finally:
        _religar("rabbitmq", "academico-despachante", "analitico-worker")

    historico = esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == "em_risco",
        "histórico atualizado depois que o broker voltou, sem novo lançamento",
        prazo=60,
    )
    assert suporte.estados(historico)[-2:] == ["sem_risco", "em_risco"]
    assert [r["status"] for r in historico].count("em_risco") == 1, "transição duplicada"
    esperar_ate(
        lambda: suporte.eventos_pendentes(inscricao["id"]),
        lambda n: n == 0,
        "outbox sem pendências depois da recuperação",
    )
    assert _mensagens(FALHAS) == falhas_antes


def test_entrega_repetida_do_mesmo_evento_e_ignorada(admin, prof_ana):
    inscricao, _ = _cenario(admin, prof_ana, nota="4.00")
    historico_antes = suporte.historico(admin, inscricao["id"])
    linha = suporte.ultimo_evento_enviado(inscricao["id"])
    envelope = json.loads(linha)
    processados_antes = suporte.total_processados()
    assert suporte.foi_processado(envelope["event_id"]), "o worker deveria ter anotado o evento"

    # O broker entrega o MESMO evento mais duas vezes (como depois de uma queda na marcação).
    for _ in range(2):
        suporte.publicar_no_broker(envelope["evento"], linha)
    esperar_ate(lambda: _mensagens(FILA), lambda n: n == 0, "fila drenada")

    registro = suporte.compose("logs", "--since", "60s", "analitico-worker").stdout
    assert registro.count("evento repetido ignorado") >= 2
    assert suporte.historico(admin, inscricao["id"]) == historico_antes
    assert suporte.total_processados() == processados_antes


def test_evento_invalido_vai_para_a_fila_de_falhas_e_o_reprocessamento_e_controlado(admin):
    suporte.compose("exec", "-T", "rabbitmq", "rabbitmqctl", "purge_queue", FALHAS)
    falhas_do_auth = _mensagens(FALHAS_AUTH)
    invalido = json.dumps({"evento": "avaliacao.alterada", "event_id": "x", "dados": {}})

    suporte.publicar_no_broker("avaliacao.alterada", invalido)

    esperar_ate(lambda: _mensagens(FALHAS), lambda n: n == 1, "evento inválido na fila de falhas")
    assert _mensagens(FILA) == 0, "evento inválido não pode ficar reentregando"
    assert _mensagens(FALHAS_AUTH) == falhas_do_auth, (
        "a falha de um serviço não vai para a fila do outro"
    )
    comando = ["exec", "-T", "analitico", "python", "-m", "app.comandos.reprocessar_falhas"]
    listagem = suporte.compose(*comando, "--listar").stdout
    assert "evento inválido" in listagem and "1 mensagem(ns) listada(s)" in listagem
    assert _mensagens(FALHAS) == 1, "listar não consome a mensagem"

    # Reprocessar sem corrigir a causa devolve a mensagem uma vez; ela volta para a fila de
    # falhas e não entra em ciclo infinito.
    assert "1 mensagem(ns) reprocessada(s)" in suporte.compose(*comando).stdout
    esperar_ate(lambda: _mensagens(FALHAS), lambda n: n == 1, "mensagem de volta à fila de falhas")
    assert _mensagens(FILA) == 0

    suporte.compose("exec", "-T", "rabbitmq", "rabbitmqctl", "purge_queue", FALHAS)


@pytest.mark.interrupcao
def test_falha_passageira_do_academico_e_tentada_de_novo_pela_fila_de_espera(admin, prof_ana):
    inscricao, avaliacao = _cenario(admin, prof_ana)
    falhas_antes = _mensagens(FALHAS)

    try:
        # Worker parado para a nota nova ficar na fila; depois derruba o acadêmico e liga o worker.
        suporte.compose("stop", "analitico-worker", timeout=60)
        dados(admin.patch(f"/academico/avaliacoes/{avaliacao['id']}", {"nota": "4.00"}))
        esperar_ate(lambda: _mensagens(FILA), lambda n: n >= 1, "evento esperando na fila")
        suporte.compose("stop", "academico", timeout=60)
        suporte.compose("up", "-d", "--no-build", "analitico-worker", timeout=60)

        # O worker não consegue consultar o acadêmico: a mensagem vai para a fila de espera.
        esperar_ate(
            lambda: _mensagens(ESPERA_5S),
            lambda n: n >= 1,
            "mensagem na fila de espera de 5 s",
            prazo=40,
            intervalo=0.2,
        )
        assert _mensagens(FALHAS) == falhas_antes, "falha passageira não vai direto para falhas"
    finally:
        _religar("academico", "academico-despachante", "analitico-worker")

    historico = esperar_ate(
        lambda: suporte.historico(admin, inscricao["id"]),
        lambda h: bool(h) and h[-1]["status"] == "em_risco",
        "histórico atualizado por uma nova tentativa, sem novo lançamento",
        prazo=120,
    )
    assert suporte.estados(historico)[-2:] == ["sem_risco", "em_risco"]
    assert _mensagens(FALHAS) == falhas_antes
