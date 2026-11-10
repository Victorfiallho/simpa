"""Métricas Prometheus do worker do analítico (etapa 6 do plano de qualidade e operação).

Expostas em `:9100/metrics` do container `analitico-worker`, só na rede interna. Nenhum rótulo
leva nome, e-mail, token ou id de aluno/inscrição: só o resultado do tratamento do evento.
"""

from datetime import UTC, datetime

from prometheus_client import Counter, Histogram, start_http_server

RESULTADOS = ("ok", "repetido", "invalido", "retentativa", "falha")

EVENTOS = Counter(
    "analitico_eventos_total",
    "Eventos recebidos pelo worker, por resultado: ok, repetido, invalido, retentativa "
    "(voltou pela fila de espera) e falha (tentativas esgotadas, foi para a fila de falhas).",
    ["resultado"],
)
RECONEXOES = Counter(
    "analitico_consumidor_reconexoes_total",
    "Vezes que o worker perdeu a conexão com o RabbitMQ e reconectou.",
)
# Do instante da alteração no acadêmico (`ocorrido_em`, no envelope) até o fim do processamento.
LATENCIA = Histogram(
    "analitico_evento_latencia_segundos",
    "Tempo entre a alteração no acadêmico e o fim do processamento do evento no worker.",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
)
PROCESSAMENTO = Histogram(
    "analitico_evento_processamento_segundos",
    "Tempo gasto só no recálculo do risco de um evento.",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30),
)

for _resultado in RESULTADOS:
    EVENTOS.labels(_resultado)


def observar_latencia(ocorrido_em: str | None) -> None:
    """Registra o tempo de ponta a ponta. Evento sem `ocorrido_em` (antigo) não conta."""
    if not ocorrido_em:
        return
    try:
        instante = datetime.fromisoformat(ocorrido_em)
    except ValueError:
        return
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    LATENCIA.observe(max(0.0, (datetime.now(UTC) - instante).total_seconds()))


def iniciar_servidor(porta: int) -> None:
    start_http_server(porta)
