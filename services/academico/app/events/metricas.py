"""Métricas Prometheus do despachante da outbox (etapa 6 do plano de qualidade e operação).

Expostas em `:9100/metrics` do container `academico-despachante`, só na rede interna. Nenhum rótulo
leva nome, e-mail, token ou id de aluno/inscrição: só o resultado da operação.
"""

from datetime import UTC, datetime

from prometheus_client import Counter, Gauge, start_http_server
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventoOutbox

RESULTADOS_PUBLICACAO = ("ok", "sem_destino", "recusado")
MOTIVOS_RECONEXAO = ("broker", "banco")

PUBLICACOES = Counter(
    "academico_despachante_publicacoes_total",
    "Tentativas de publicação da outbox no RabbitMQ, por resultado.",
    ["resultado"],
)
RECONEXOES = Counter(
    "academico_despachante_reconexoes_total",
    "Vezes que o despachante perdeu o RabbitMQ ou o banco e precisou reconectar.",
    ["motivo"],
)
PENDENTES = Gauge(
    "academico_outbox_eventos_pendentes", "Eventos da outbox que ainda não foram publicados."
)
IDADE_DO_MAIS_ANTIGO = Gauge(
    "academico_outbox_idade_evento_mais_antigo_segundos",
    "Idade do evento pendente mais antigo da outbox (0 quando não há pendentes).",
)
ULTIMO_CICLO = Gauge(
    "academico_despachante_ultimo_ciclo_timestamp_segundos",
    "Instante (Unix) do último ciclo do despachante: se parar de avançar, ele travou.",
)

# As séries existem desde o início: sem isso `increase()` e a detecção de série ausente enganam.
for _resultado in RESULTADOS_PUBLICACAO:
    PUBLICACOES.labels(_resultado)
for _motivo in MOTIVOS_RECONEXAO:
    RECONEXOES.labels(_motivo)


def atualizar_outbox(db: Session, agora: datetime | None = None) -> None:
    """Atualiza os medidores da outbox: quantos esperam e há quanto tempo o mais antigo espera."""
    agora = agora or datetime.now(UTC)
    pendentes, mais_antigo = db.execute(
        select(func.count(), func.min(EventoOutbox.criado_em)).where(
            EventoOutbox.enviado_em.is_(None)
        )
    ).one()
    PENDENTES.set(pendentes)
    if mais_antigo is None:
        IDADE_DO_MAIS_ANTIGO.set(0)
        return
    if mais_antigo.tzinfo is None:  # SQLite devolve sem fuso; tudo é gravado em UTC
        mais_antigo = mais_antigo.replace(tzinfo=UTC)
    IDADE_DO_MAIS_ANTIGO.set(max(0.0, (agora - mais_antigo).total_seconds()))


def iniciar_servidor(porta: int) -> None:
    start_http_server(porta)
