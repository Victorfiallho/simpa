"""Envio do registro de auditoria de cada requisição (RF12, RNF16).

Ao fim de cada requisição, o serviço publica o evento `log.requisicao` no RabbitMQ. Quem grava
na tabela `log_requisicao` (banco do auth) é o worker do auth. Assim nenhum serviço acessa o
banco de outro (D13) e uma falha no RabbitMQ nunca derruba a requisição do usuário.

O registro tem só campos fixos: nunca corpo, cabeçalhos, query string, senha, token ou CPF
(RNF04). Como o CPF pode aparecer no caminho de uma rota, ele é mascarado antes de sair.
"""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime

import pika

from app.core.config import get_settings

EXCHANGE = "simpa.eventos"
CHAVE = "log.requisicao"
CAMPOS = (
    "correlation_id",
    "usuario_id",
    "rota",
    "metodo_http",
    "status_http",
    "ip_origem",
    "tempo_resposta_ms",
    "timestamp",
)
# CPF com ou sem pontuação (11 dígitos), sem pegar trechos de números maiores.
_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")

logger = logging.getLogger("auditoria")


def mascarar(rota: str) -> str:
    return _CPF.sub("***.***.***-**", rota)[:300]


def montar_registro(
    *,
    correlation_id: str,
    usuario_id: int | None,
    rota: str,
    metodo: str,
    status_http: int,
    ip_origem: str,
    tempo_ms: int,
) -> dict:
    return {
        "correlation_id": correlation_id[:64],
        "usuario_id": usuario_id,
        "rota": mascarar(rota),
        "metodo_http": metodo[:10],
        "status_http": status_http,
        "ip_origem": ip_origem[:45],
        "tempo_resposta_ms": tempo_ms,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def deve_registrar(rota: str) -> bool:
    """Healthcheck e rotas internas (serviço a serviço) não são ações de usuário."""
    return rota != "/health" and not rota.startswith("/internal")


def enviar(registro: dict) -> None:
    """Dispara a publicação em outra thread, sem atrasar a resposta nem travar o servidor."""
    asyncio.get_running_loop().run_in_executor(None, publicar_registro, registro)


def publicar_registro(registro: dict) -> None:
    """Publica o registro; se o RabbitMQ estiver fora, só avisa no log."""
    corpo = json.dumps(
        {"evento": CHAVE, "request_id": registro["correlation_id"], "dados": registro},
        ensure_ascii=False,
    )
    try:
        with pika.BlockingConnection(pika.URLParameters(get_settings().rabbitmq_url)) as conexao:
            canal = conexao.channel()
            canal.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
            canal.basic_publish(
                exchange=EXCHANGE,
                routing_key=CHAVE,
                body=corpo.encode(),
                properties=pika.BasicProperties(
                    content_type="application/json", delivery_mode=pika.DeliveryMode.Persistent
                ),
            )
    except Exception:
        logger.warning("não foi possível enviar o registro de auditoria", exc_info=True)
