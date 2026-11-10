"""Worker que consome os eventos do acadêmico e recalcula o risco (RF03, RF07, D11, D14).

Roda em um container próprio (analitico-worker):  python -m app.events.consumidor

Tratamento de cada mensagem:
- Evento repetido (mesmo `event_id`): ignorado com ack. A entrega é "pelo menos uma vez".
- Evento inválido (JSON quebrado, campo ausente): vai direto para a fila de falhas, sem novas
  tentativas.
- Falha possivelmente passageira (acadêmico fora do ar, banco indisponível): volta pela fila de
  espera, depois de 5 s, 30 s e 2 min. Esgotadas as tentativas, vai para a fila de falhas.
- A fila de falhas guarda o motivo nos cabeçalhos (`x-erro`, `x-tentativas`). Para reprocessar:
  python -m app.comandos.reprocessar_falhas
"""

import json
import logging
import os
import time
from datetime import UTC, datetime

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.core.config import get_settings
from app.core.logs import configurar_logs, request_id_atual
from app.events import metricas
from app.services import eventos
from app.services.risco import recalcular_risco_da_inscricao

EXCHANGE = "simpa.eventos"
# Legado: as duas filas de falha (analítico e auth) estão ligadas a esta exchange `fanout`, que
# entrega cada mensagem às duas. Mantida só porque trocar o argumento da fila principal exigiria
# recriá-la; as falhas agora vão direto para a fila de falhas do próprio serviço.
EXCHANGE_FALHAS = "simpa.eventos.falhas"
EXCHANGE_ESPERA = "simpa.eventos.espera"
FILA = "analitico.recalculo-risco"
FILA_FALHAS = "analitico.recalculo-risco.falhas"
CHAVES = ("avaliacao.*", "frequencia.*", "inscricao.*")
# Espera, em segundos, antes de cada nova tentativa. O tamanho da tupla é o limite de tentativas.
ESPERAS = (5, 30, 120)

logger = logging.getLogger("analitico.eventos")

# Broker indisponível: erros do AMQP e também os de rede. Com o contêiner do RabbitMQ parado o nome
# dele deixa de existir na rede do Docker e o pika levanta `socket.gaierror`, que é um `OSError`
# e NÃO um `AMQPError`. Sem capturá-lo, o processo morria em vez de reconectar.
ERROS_DO_BROKER = (pika.exceptions.AMQPError, OSError)


def fila_de_espera(segundos: int) -> str:
    return f"{FILA}.espera.{segundos}s"


def declarar_topologia(canal: BlockingChannel) -> None:
    """Cria exchanges e filas se ainda não existirem (operação idempotente)."""
    canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
    canal.exchange_declare(EXCHANGE_FALHAS, exchange_type="fanout", durable=True)
    canal.exchange_declare(EXCHANGE_ESPERA, exchange_type="direct", durable=True)
    canal.queue_declare(FILA_FALHAS, durable=True)
    canal.queue_bind(FILA_FALHAS, EXCHANGE_FALHAS)
    canal.queue_declare(FILA, durable=True, arguments={"x-dead-letter-exchange": EXCHANGE_FALHAS})
    for chave in CHAVES:
        canal.queue_bind(FILA, EXCHANGE, routing_key=chave)
    # Filas de espera: a mensagem fica parada pelo TTL e volta para a fila principal.
    for segundos in ESPERAS:
        fila = fila_de_espera(segundos)
        canal.queue_declare(
            fila,
            durable=True,
            arguments={
                "x-message-ttl": segundos * 1000,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": FILA,
            },
        )
        canal.queue_bind(fila, EXCHANGE_ESPERA, routing_key=str(segundos))


def _cabecalhos(propriedades: BasicProperties | None) -> dict:
    return dict(getattr(propriedades, "headers", None) or {})


def _propriedades(cabecalhos: dict, original: BasicProperties | None) -> BasicProperties:
    return pika.BasicProperties(
        content_type="application/json",
        delivery_mode=pika.DeliveryMode.Persistent,
        message_id=getattr(original, "message_id", None),
        headers=cabecalhos,
    )


def _para_a_fila_de_falhas(
    canal: BlockingChannel,
    metodo: Basic.Deliver,
    propriedades: BasicProperties | None,
    corpo: bytes,
    motivo: str,
) -> None:
    """Guarda a mensagem com o motivo e confirma a original. Não tenta de novo sozinha."""
    cabecalhos = _cabecalhos(propriedades)
    cabecalhos.update(
        {
            "x-erro": motivo[:300],
            "x-falhou-em": datetime.now(UTC).isoformat(),
            "x-chave": metodo.routing_key,
        }
    )
    # Direto na fila de falhas deste serviço (exchange padrão, chave = nome da fila). Não use a
    # exchange de falhas: ela é `fanout` e entregaria também à fila de falhas do outro serviço.
    canal.basic_publish("", FILA_FALHAS, corpo, _propriedades(cabecalhos, propriedades))
    canal.basic_ack(delivery_tag=metodo.delivery_tag)
    logger.error("evento enviado para a fila de falhas", extra={"dados": {"motivo": motivo[:300]}})


def _tentar_de_novo(
    canal: BlockingChannel,
    metodo: Basic.Deliver,
    propriedades: BasicProperties | None,
    corpo: bytes,
    erro: Exception,
) -> None:
    cabecalhos = _cabecalhos(propriedades)
    tentativas = int(cabecalhos.get("x-tentativas", 0))
    motivo = f"{type(erro).__name__}: {erro}"
    if tentativas >= len(ESPERAS):
        metricas.EVENTOS.labels("falha").inc()
        cabecalhos["x-tentativas"] = tentativas
        _para_a_fila_de_falhas(
            canal, metodo, propriedades, corpo, f"tentativas esgotadas: {motivo}"
        )
        return
    metricas.EVENTOS.labels("retentativa").inc()
    espera = ESPERAS[tentativas]
    cabecalhos.update({"x-tentativas": tentativas + 1, "x-ultimo-erro": motivo[:300]})
    canal.basic_publish(
        EXCHANGE_ESPERA, str(espera), corpo, _propriedades(cabecalhos, propriedades)
    )
    canal.basic_ack(delivery_tag=metodo.delivery_tag)
    logger.warning(
        "falha ao processar evento; nova tentativa agendada",
        extra={"dados": {"tentativa": tentativas + 1, "espera_s": espera, "motivo": motivo[:300]}},
    )


def processar(
    canal: BlockingChannel, metodo: Basic.Deliver, propriedades: BasicProperties, corpo: bytes
) -> None:
    """Processa um evento. Ack só depois de terminar ou de a mensagem ter outro destino seguro."""
    token = request_id_atual.set("-")
    try:
        try:
            mensagem = json.loads(corpo)
            inscricao_id = int(mensagem["dados"]["inscricao_id"])
        except (ValueError, KeyError, TypeError) as erro:
            metricas.EVENTOS.labels("invalido").inc()
            _para_a_fila_de_falhas(canal, metodo, propriedades, corpo, f"evento inválido: {erro!r}")
            return

        request_id_atual.set(mensagem.get("request_id", "-"))
        evento_id = mensagem.get("event_id")
        if evento_id and eventos.ja_processado(evento_id):
            metricas.EVENTOS.labels("repetido").inc()
            logger.info("evento repetido ignorado", extra={"dados": {"event_id": evento_id}})
            canal.basic_ack(delivery_tag=metodo.delivery_tag)
            return

        try:
            with metricas.PROCESSAMENTO.time():
                recalcular_risco_da_inscricao(inscricao_id)
            if evento_id:
                eventos.marcar_processado(evento_id)
        except Exception as erro:
            logger.exception(
                "falha ao processar evento", extra={"dados": {"chave": metodo.routing_key}}
            )
            _tentar_de_novo(canal, metodo, propriedades, corpo, erro)
            return
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
        metricas.EVENTOS.labels("ok").inc()
        metricas.observar_latencia(mensagem.get("ocorrido_em"))
    finally:
        request_id_atual.reset(token)


def main() -> None:
    configurar_logs("analitico")
    metricas.iniciar_servidor(int(os.environ.get("METRICAS_PORTA", "9100")))
    parametros = pika.URLParameters(get_settings().rabbitmq_url)
    while True:
        try:
            with pika.BlockingConnection(parametros) as conexao:
                canal = conexao.channel()
                canal.confirm_delivery()
                declarar_topologia(canal)
                canal.basic_qos(prefetch_count=1)
                canal.basic_consume(queue=FILA, on_message_callback=processar)
                logger.info("aguardando eventos", extra={"dados": {"fila": FILA}})
                canal.start_consuming()
        except ERROS_DO_BROKER:
            metricas.RECONEXOES.inc()
            logger.warning("RabbitMQ indisponível; nova tentativa em 5 s")
            time.sleep(5)


if __name__ == "__main__":
    main()
