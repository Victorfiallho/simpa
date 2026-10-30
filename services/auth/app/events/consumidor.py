"""Worker que grava a auditoria das requisições (RF12, RNF16, D14).

Roda em um container próprio (auth-worker):  python -m app.events.consumidor

Consome o evento `log.requisicao`, publicado por todos os serviços. Uma mensagem inválida ou
que falha vai para a fila de falhas (auth.auditoria.falhas) em vez de sumir.
"""

import json
import logging
import time

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.core.config import get_settings
from app.core.database import get_sessionmaker
from app.core.logs import configurar_logs
from app.services.auditoria import gravar_registro

EXCHANGE = "simpa.eventos"
EXCHANGE_FALHAS = "simpa.eventos.falhas"
FILA = "auth.auditoria"
FILA_FALHAS = "auth.auditoria.falhas"
CHAVE = "log.requisicao"

logger = logging.getLogger("auth.eventos")


def declarar_topologia(canal: BlockingChannel) -> None:
    """Cria exchanges e filas se ainda não existirem (operação idempotente)."""
    canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_FALHAS, exchange_type="fanout", durable=True)
    canal.queue_declare(FILA_FALHAS, durable=True)
    canal.queue_bind(FILA_FALHAS, EXCHANGE_FALHAS)
    canal.queue_declare(FILA, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_FALHAS})
    canal.queue_bind(FILA, EXCHANGE, routing_key=CHAVE)


def processar(
    canal: BlockingChannel, metodo: Basic.Deliver, _propriedades: BasicProperties, corpo: bytes
) -> None:
    """Grava o registro. Ack só depois de gravar; se falhar, vai para a fila de falhas."""
    try:
        mensagem = json.loads(corpo)
        with get_sessionmaker()() as db:
            gravar_registro(db, mensagem["dados"])
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
    except Exception:
        # Sem o corpo no log: ele traz IP e rota de um usuário.
        logger.exception("falha ao gravar auditoria")
        canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)


def main() -> None:
    configurar_logs("auth")
    parametros = pika.URLParameters(get_settings().rabbitmq_url)
    while True:
        try:
            with pika.BlockingConnection(parametros) as conexao:
                canal = conexao.channel()
                declarar_topologia(canal)
                canal.basic_qos(prefetch_count=20)
                canal.basic_consume(queue=FILA, on_message_callback=processar)
                logger.info("aguardando registros de auditoria")
                canal.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ indisponível; nova tentativa em 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()
