"""Despachante da outbox: publica no RabbitMQ os eventos gravados pelo acadêmico (D14).

Roda em um container próprio (academico-despachante):  python -m app.events.despachante

Garantias:
- O evento só é marcado como enviado (`enviado_em`) DEPOIS da confirmação do broker
  (publisher confirm). Se o processo cair entre o envio e a marcação, o evento é enviado de
  novo: a entrega é "pelo menos uma vez", e o consumidor ignora repetições pelo `event_id`.
- A publicação usa `mandatory`: sem fila ligada à exchange, o broker devolve a mensagem e o
  evento continua pendente (com espera progressiva), em vez de se perder em silêncio.
- Vários despachantes podem rodar juntos: cada um pega o próximo evento com
  `FOR UPDATE SKIP LOCKED`, sem disputar a mesma linha.
- Com o broker fora do ar, nada é perdido: os eventos esperam na tabela e saem quando ele volta.
"""

import json
import logging
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPError, NackError, UnroutableError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.logs import configurar_logs, request_id_atual
from app.events import metricas
from app.models import EventoOutbox

EXCHANGE = "simpa.eventos"
ESPERA_MAXIMA_SEGUNDOS = 300
INTERVALO_SEGUNDOS = 0.5
ATUALIZACAO_DAS_METRICAS_SEGUNDOS = 5
LOTE_MAXIMO = 200
# O healthcheck do container confere se este arquivo foi tocado há pouco.
VIVO = Path("/tmp/despachante.ativo")  # noqa: S108 (arquivo de vida do próprio container)

logger = logging.getLogger("academico.despachante")

# Broker indisponível: erros do AMQP e também os de rede. Com o contêiner do RabbitMQ parado o nome
# dele deixa de existir na rede do Docker e o pika levanta `socket.gaierror`, que é um `OSError`
# e NÃO um `AMQPError`. Sem capturá-lo, o processo morria em vez de reconectar.
ERROS_DO_BROKER = (AMQPError, OSError)


def espera_progressiva(tentativas: int) -> timedelta:
    """2 s, 4 s, 8 s… até 5 minutos, para não martelar um destino que ainda não existe."""
    return timedelta(seconds=min(2**tentativas, ESPERA_MAXIMA_SEGUNDOS))


def despachar_um(db: Session, canal: BlockingChannel, agora: datetime) -> bool:
    """Publica o próximo evento pendente e vencido. Devolve False quando não há nenhum."""
    evento = db.scalars(
        select(EventoOutbox)
        .where(EventoOutbox.enviado_em.is_(None), EventoOutbox.proxima_tentativa_em <= agora)
        .order_by(EventoOutbox.criado_em, EventoOutbox.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()
    if evento is None:
        return False

    request_id_atual.set(json.loads(evento.corpo).get("request_id", "-"))
    try:
        canal.basic_publish(
            exchange=EXCHANGE,
            routing_key=evento.chave,
            body=evento.corpo.encode(),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=evento.id,
            ),
            mandatory=True,
        )
    except (UnroutableError, NackError) as erro:
        # O broker recebeu a conexão mas não aceitou a mensagem (sem fila ligada ou recusa):
        # continua pendente, para uma nova tentativa depois de uma espera maior a cada vez.
        metricas.PUBLICACOES.labels(
            "sem_destino" if isinstance(erro, UnroutableError) else "recusado"
        ).inc()
        evento.tentativas += 1
        evento.ultimo_erro = f"{type(erro).__name__}: {erro}"[:500]
        evento.proxima_tentativa_em = agora + espera_progressiva(evento.tentativas)
        db.commit()
        logger.warning(
            "evento sem destino ou recusado; nova tentativa agendada",
            extra={
                "dados": {
                    "event_id": evento.id,
                    "chave": evento.chave,
                    "tentativas": evento.tentativas,
                }
            },
        )
        return True

    evento.enviado_em = agora
    evento.ultimo_erro = None
    db.commit()
    metricas.PUBLICACOES.labels("ok").inc()
    logger.info("evento publicado", extra={"dados": {"event_id": evento.id, "chave": evento.chave}})
    return True


def despachar_pendentes(
    fabrica: sessionmaker[Session], canal: BlockingChannel, limite: int = LOTE_MAXIMO
) -> int:
    """Despacha os eventos vencidos, um por transação curta. Devolve quantos foram tratados."""
    tratados = 0
    while tratados < limite:
        with fabrica() as db:
            if not despachar_um(db, canal, datetime.now(UTC)):
                break
        tratados += 1
    return tratados


def atualizar_metricas(fabrica: sessionmaker[Session]) -> bool:
    """Atualiza os medidores da outbox. Nunca levanta: devolve False se o banco falhar."""
    try:
        with fabrica() as db:
            metricas.atualizar_outbox(db)
    except Exception:
        logger.exception("falha ao atualizar as métricas da outbox")
        return False
    return True


def _laco_das_metricas(fabrica: sessionmaker[Session]) -> None:
    """Atualiza os medidores da outbox em uma thread própria, a cada poucos segundos.

    Tem de ser independente da conexão com o RabbitMQ: com o broker fora do ar o despachante fica
    preso reconectando, e é exatamente aí que a idade do evento mais antigo precisa continuar
    subindo para o alerta enxergar o atraso.
    """
    while True:
        atualizar_metricas(fabrica)
        time.sleep(ATUALIZACAO_DAS_METRICAS_SEGUNDOS)


def main() -> None:
    configurar_logs("academico-despachante")
    metricas.iniciar_servidor(int(os.environ.get("METRICAS_PORTA", "9100")))
    parametros = pika.URLParameters(get_settings().rabbitmq_url)
    fabrica = get_sessionmaker()
    threading.Thread(
        target=_laco_das_metricas, args=(fabrica,), daemon=True, name="metricas-da-outbox"
    ).start()
    while True:
        try:
            with pika.BlockingConnection(parametros) as conexao:
                canal = conexao.channel()
                canal.confirm_delivery()
                canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
                logger.info("despachante pronto", extra={"dados": {"exchange": EXCHANGE}})
                while True:
                    VIVO.touch()
                    metricas.ULTIMO_CICLO.set_to_current_time()
                    if despachar_pendentes(fabrica, canal) == 0:
                        # Espera sem deixar a conexão sem batimento (heartbeat) do broker.
                        conexao.process_data_events(time_limit=INTERVALO_SEGUNDOS)
        except ERROS_DO_BROKER:
            metricas.RECONEXOES.labels("broker").inc()
            logger.warning("RabbitMQ indisponível; nova tentativa em 5 s")
            time.sleep(5)
        except SQLAlchemyError:
            metricas.RECONEXOES.labels("banco").inc()
            # Falha entre o envio e a marcação: o evento volta a ficar pendente e será reenviado.
            logger.exception("falha no banco ao despachar; nova tentativa em 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()
