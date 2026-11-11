"""Simulações do monitoramento das filas (etapa 6 do plano de qualidade e operação).

Parte do mesmo ambiente isolado, com a camada de monitoramento:
    docker compose --env-file .env.test -p simpa-test -f compose.test.yml \\
        -f compose.monitoramento.yml up -d --wait

Cada alerta é visto passar de normal para ativo e voltar ao normal, e a notificação chega ao
receptor LOCAL de teste (nada sai para pessoas nem canais externos). Os limites de tempo vêm das
regras (`for:`): os testes esperam o tempo real. A lógica de cada regra, inclusive as lentas, é
provada à parte com `promtool test rules` (infra/monitoramento/prometheus/regras.test.yml).
"""

from __future__ import annotations

import json

import pytest

from tests.integration import suporte
from tests.integration.suporte import esperar_ate

pytestmark = pytest.mark.skipif(
    not suporte.monitoramento_no_ar(),
    reason="monitoramento fora do ar: suba com -f compose.test.yml -f compose.monitoramento.yml",
)

FILA = "analitico.recalculo-risco"
FALHAS = "analitico.recalculo-risco.falhas"


def _normal(nome: str, **rotulos: str):
    return lambda: (
        not any(
            a["nome"] == nome and all(a.get(k) == v for k, v in rotulos.items())
            for a in suporte.alertas_do_prometheus()
        )
    )


def _notificacoes_de(nome: str, estado: str, desde: int) -> list[dict]:
    return [
        n
        for n in suporte.notificacoes_recebidas()[desde:]
        if n["alerta"] == nome and n["estado"] == estado
    ]


def _religar(*servicos: str) -> None:
    """Liga os serviços e espera todos ficarem saudáveis.

    Não usa `up --wait`: ele desiste ao ver um contêiner `unhealthy`, e depois de alguns minutos sem
    o broker o despachante está mesmo `unhealthy` (não completa ciclos). É o esperado, e ele se
    recupera sozinho quando o broker volta.
    """
    suporte.compose("start", *servicos, timeout=120)
    esperar_ate(
        lambda: {s: suporte.saude_dos_servicos().get(s) for s in servicos},
        lambda saude: all(v == "healthy" for v in saude.values()),
        f"serviços saudáveis de novo: {', '.join(servicos)}",
        prazo=180,
        intervalo=3,
    )


def _lancar(admin, prof) -> int:
    """Cria um cenário e lança uma nota. Devolve o id da inscrição, para conferir o histórico."""
    turma = suporte.criar_turma(admin)
    disciplina = suporte.criar_disciplina(admin, turma["id"], prof.usuario_id)
    aluno = suporte.criar_aluno(admin, turma["id"])
    inscricao = suporte.inscrever(admin, aluno["id"], disciplina["id"])
    suporte.lancar_nota(admin, inscricao["id"], "8.00")
    suporte.lancar_frequencia(admin, inscricao["id"], faltas=1)  # sem frequência não há situação
    return inscricao["id"]


@pytest.mark.interrupcao
def test_worker_parado_dispara_fila_sem_consumidor_e_volta_ao_normal(admin, prof_ana):
    assert _normal("FilaSemConsumidor")(), "o ambiente deveria começar sem alertas de fila"
    desde = len(suporte.notificacoes_recebidas())
    try:
        suporte.compose("stop", "analitico-worker", timeout=60)
        _lancar(admin, prof_ana)  # a fila acumula enquanto ninguém consome

        # Dispara só depois de 1 minuto sem consumidor (a regra tem `for: 1m`): antes é oscilação.
        esperar_ate(
            lambda: suporte.disparado("FilaSemConsumidor", queue=FILA),
            bool,
            "alerta FilaSemConsumidor ativo",
            prazo=150,
            intervalo=3,
        )
        # O worker parado também some da coleta: o alerta de coleta acompanha.
        esperar_ate(
            lambda: suporte.disparado("ColetaDeMetricasAusente", job="analitico-worker"),
            bool,
            "alerta de coleta do worker",
            prazo=90,
            intervalo=3,
        )
        esperar_ate(
            lambda: _notificacoes_de("FilaSemConsumidor", "firing", desde),
            bool,
            "notificação FilaSemConsumidor chegou ao receptor",
            prazo=90,
            intervalo=3,
        )
    finally:
        _religar("analitico-worker")

    esperar_ate(
        _normal("FilaSemConsumidor", queue=FILA),
        bool,
        "FilaSemConsumidor voltou ao normal",
        prazo=120,
        intervalo=3,
    )
    esperar_ate(
        lambda: _notificacoes_de("FilaSemConsumidor", "resolved", desde),
        bool,
        "notificação de normalização chegou ao receptor",
        prazo=120,
        intervalo=3,
    )


def test_evento_invalido_dispara_fila_de_falhas_e_volta_ao_normal(admin):
    suporte.compose("exec", "-T", "rabbitmq", "rabbitmqctl", "purge_queue", FALHAS)
    esperar_ate(_normal("FilaDeFalhasRecebeuMensagens"), bool, "começa sem alerta de falhas",
                prazo=90, intervalo=3)  # fmt: skip
    desde = len(suporte.notificacoes_recebidas())

    try:
        invalido = json.dumps({"evento": "avaliacao.alterada", "event_id": "x", "dados": {}})
        suporte.publicar_no_broker("avaliacao.alterada", invalido)

        esperar_ate(
            lambda: suporte.disparado("FilaDeFalhasRecebeuMensagens", queue=FALHAS),
            bool,
            "alerta FilaDeFalhasRecebeuMensagens ativo",
            prazo=90,
            intervalo=3,
        )
        esperar_ate(
            lambda: _notificacoes_de("FilaDeFalhasRecebeuMensagens", "firing", desde),
            bool,
            "notificação da fila de falhas chegou ao receptor",
            prazo=90,
            intervalo=3,
        )
        # A falha do analítico não pode acender a fila de falhas do auth (defeito da etapa 4).
        assert not suporte.disparado("FilaDeFalhasRecebeuMensagens", queue="auth.auditoria.falhas")
    finally:
        # Depois de examinar o caso: descarta o evento inválido do teste (só no ambiente de teste).
        suporte.compose("exec", "-T", "rabbitmq", "rabbitmqctl", "purge_queue", FALHAS)

    esperar_ate(_normal("FilaDeFalhasRecebeuMensagens"), bool, "alerta de falhas voltou ao normal",
                prazo=120, intervalo=3)  # fmt: skip
    esperar_ate(
        lambda: _notificacoes_de("FilaDeFalhasRecebeuMensagens", "resolved", desde),
        bool,
        "notificação de normalização chegou ao receptor",
        prazo=120,
        intervalo=3,
    )


@pytest.mark.interrupcao
def test_broker_parado_mostra_o_atraso_na_outbox_e_a_inibicao_evita_ruido(admin, prof_ana):
    desde = len(suporte.notificacoes_recebidas())
    try:
        suporte.compose("stop", "rabbitmq", timeout=60)
        inscricao_id = _lancar(admin, prof_ana)  # o acadêmico grava; o evento espera na outbox

        esperar_ate(
            lambda: suporte.disparado("EventoPendenteNaOutbox"),
            bool,
            "alerta EventoPendenteNaOutbox (evento esperando há mais de 2 minutos)",
            prazo=240,
            intervalo=5,
        )
        # A notificação precisa chegar com o broker ainda fora: se ele voltar antes, a outbox
        # esvazia, o alerta se resolve sem ter sido notificado e não há "resolvido" a esperar
        # (visto em um runner lento do CI).
        esperar_ate(
            lambda: _notificacoes_de("EventoPendenteNaOutbox", "firing", desde),
            bool,
            "notificação EventoPendenteNaOutbox chegou ao receptor",
            prazo=90,
            intervalo=3,
        )
        esperar_ate(
            lambda: suporte.disparado("ColetaDeMetricasAusente", job="rabbitmq"),
            bool,
            "alerta de coleta do RabbitMQ",
            prazo=60,
            intervalo=3,
        )
        # Sem coletar o RabbitMQ, "a fila sumiu" é consequência: o Alertmanager mantém inibido.
        esperar_ate(
            lambda: "FilaEsperadaAusente" in suporte.alertas_inibidos(),
            bool,
            "FilaEsperadaAusente inibido como consequência",
            prazo=90,
            intervalo=3,
        )
        assert not _notificacoes_de("FilaEsperadaAusente", "firing", desde)
    finally:
        _religar("rabbitmq", "academico-despachante", "analitico-worker")

    for nome in ("EventoPendenteNaOutbox", "ColetaDeMetricasAusente"):
        esperar_ate(_normal(nome), bool, f"{nome} voltou ao normal", prazo=180, intervalo=3)
    esperar_ate(
        lambda: _notificacoes_de("EventoPendenteNaOutbox", "resolved", desde),
        bool,
        "notificação de normalização da outbox chegou ao receptor",
        prazo=120,
        intervalo=3,
    )
    # Nada se perdeu: o evento que esperou na outbox chegou e o histórico foi atualizado.
    esperar_ate(
        lambda: suporte.historico(admin, inscricao_id),
        lambda h: bool(h) and h[-1]["status"] == "sem_risco",
        "o evento que esperou na outbox chegou ao histórico",
        prazo=90,
    )
