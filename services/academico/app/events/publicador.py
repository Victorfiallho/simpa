"""Publica eventos de domínio no RabbitMQ (D14).

O acadêmico só avisa que algo mudou; não sabe quem vai consumir. Hoje quem consome é
o worker do analítico, que recalcula o risco da inscrição (RF03, RF07).

Eventos previstos (chave de roteamento → dados):
    avaliacao.alterada   → {"inscricao_id": int}
    frequencia.alterada  → {"inscricao_id": int}
    inscricao.alterada   → {"inscricao_id": int}
"""

import json
from typing import Any

import pika

from app.core.config import get_settings
from app.core.logs import request_id_atual

EXCHANGE = "simpa.eventos"


def publicar(chave: str, dados: dict[str, Any]) -> None:
    """Publica um evento persistente na exchange do SIMPA.

    Chame só DEPOIS do commit, para não anunciar algo que foi desfeito. Usa conexão
    bloqueante: chame a partir de rotas `def` (não `async def`).
    """
    corpo = json.dumps({"evento": chave, "request_id": request_id_atual.get(), "dados": dados})
    with pika.BlockingConnection(pika.URLParameters(get_settings().rabbitmq_url)) as conexao:
        canal = conexao.channel()
        canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
        canal.basic_publish(
            exchange=EXCHANGE,
            routing_key=chave,
            body=corpo.encode(),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
