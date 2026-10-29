"""Worker que consome os eventos do acadêmico e recalcula o risco (RF03, RF07, D11, D14).

Roda em um container próprio (analitico-worker):  python -m app.events.consumidor

Uma mensagem que falha vai para a fila de falhas (analitico.recalculo-risco.falhas)
em vez de sumir. Dá para inspecioná-la no painel do RabbitMQ.
"""

import json
import logging
import time

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.core.config import get_settings
from app.core.logs import configurar_logs, request_id_atual
from app.services.risco import recalcular_risco_da_inscricao

EXCHANGE = "simpa.eventos"
EXCHANGE_FALHAS = "simpa.eventos.falhas"
FILA = "analitico.recalculo-risco"
FILA_FALHAS = "analitico.recalculo-risco.falhas"
CHAVES = ("avaliacao.*", "frequencia.*", "inscricao.*")

logger = logging.getLogger("analitico.eventos")


def declarar_topologia(canal: BlockingChannel) -> None:
    """Cria exchanges e filas se ainda não existirem (operação idempotente)."""
    canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_FALHAS, exchange_type="fanout", durable=True)
    canal.queue_declare(FILA_FALHAS, durable=True)
    canal.queue_bind(FILA_FALHAS, EXCHANGE_FALHAS)
    canal.queue_declare(FILA, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_FALHAS})
    for chave in CHAVES:
        canal.queue_bind(FILA, EXCHANGE, routing_key=chave)


def processar(
    canal: BlockingChannel, metodo: Basic.Deliver, _propriedades: BasicProperties, corpo: bytes
) -> None:
    """Processa um evento. Ack só depois de terminar; se falhar, manda para a fila de falhas."""
    token = request_id_atual.set("-")
    try:
        mensagem = json.loads(corpo)
        request_id_atual.set(mensagem.get("request_id", "-"))
        recalcular_risco_da_inscricao(int(mensagem["dados"]["inscricao_id"]))
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
    except Exception:
        logger.exception(
            "falha ao processar evento", extra={"dados": {"chave": metodo.routing_key}}
        )
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
    finally:
        request_id_atual.reset(token)


def main() -> None:
    configurar_logs("analitico")
    parametros = pika.URLParameters(get_settings().rabbitmq_url)
    while True:
        try:
            with pika.BlockingConnection(parametros) as conexao:
                canal = conexao.channel()
                declarar_topologia(canal)
                canal.basic_qos(prefetch_count=1)
                canal.basic_consume(queue=FILA, on_message_callback=processar)
                logger.info("aguardando eventos", extra={"dados": {"fila": FILA}})
                canal.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ indisponível; nova tentativa em 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()
