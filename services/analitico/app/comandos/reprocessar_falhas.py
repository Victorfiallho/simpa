"""Reprocessa os eventos da fila de falhas, depois de corrigida a causa.

Uso (dentro do container do analítico):
    python -m app.comandos.reprocessar_falhas --listar      # só mostra, sem mexer
    python -m app.comandos.reprocessar_falhas               # devolve todos à fila principal
    python -m app.comandos.reprocessar_falhas --limite 10   # só os 10 primeiros

Cada mensagem é devolvida UMA vez por execução, com o contador de tentativas zerado. Reprocessar é
seguro: o worker ignora o `event_id` já tratado e o recálculo do risco parte do estado atual.
Antes de rodar, descubra o motivo (cabeçalho `x-erro`) e corrija a causa: um evento inválido volta
para a fila de falhas se for reprocessado sem correção.
"""

import argparse
import json

import pika
from pika.adapters.blocking_connection import BlockingChannel

from app.core.config import get_settings
from app.events.consumidor import FILA, FILA_FALHAS

LIMITE_DA_LISTA = 1000
CABECALHOS_DE_FALHA = ("x-tentativas", "x-ultimo-erro", "x-erro", "x-falhou-em")


def _event_id(corpo: bytes) -> str:
    try:
        return str(json.loads(corpo).get("event_id", "-"))
    except (ValueError, AttributeError):
        return "(corpo ilegível)"


def listar(canal: BlockingChannel, limite: int) -> int:
    """Mostra as mensagens da fila de falhas sem consumir nenhuma.

    Lê um retrato do tamanho atual da fila e só devolve tudo no final: se cada mensagem fosse
    devolvida na hora, a leitura seguinte pegaria a mesma de novo.
    """
    tamanho = canal.queue_declare(FILA_FALHAS, passive=True).method.message_count
    ultima = None
    lidas = 0
    for _ in range(min(tamanho, limite or LIMITE_DA_LISTA, LIMITE_DA_LISTA)):
        metodo, propriedades, corpo = canal.basic_get(FILA_FALHAS, auto_ack=False)
        if metodo is None:
            break
        cabecalhos = propriedades.headers or {}
        print(
            f"event_id={_event_id(corpo)} chave={cabecalhos.get('x-chave')} "
            f"tentativas={cabecalhos.get('x-tentativas', 0)} erro={cabecalhos.get('x-erro')}"
        )
        ultima = metodo.delivery_tag
        lidas += 1
    if ultima is not None:
        canal.basic_nack(delivery_tag=ultima, multiple=True, requeue=True)
    return lidas


def reprocessar(canal: BlockingChannel, limite: int) -> int:
    """Devolve à fila principal as mensagens da fila de falhas, no máximo `limite` (0 = todas)."""
    tamanho = canal.queue_declare(FILA_FALHAS, passive=True).method.message_count
    devolvidas = 0
    for _ in range(min(tamanho, limite) if limite else tamanho):
        metodo, propriedades, corpo = canal.basic_get(FILA_FALHAS, auto_ack=False)
        if metodo is None:
            break
        cabecalhos = {
            k: v for k, v in (propriedades.headers or {}).items() if k not in CABECALHOS_DE_FALHA
        }
        cabecalhos["x-reprocessado"] = True
        canal.basic_publish(
            "",
            FILA,
            corpo,
            pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=propriedades.message_id,
                headers=cabecalhos,
            ),
            mandatory=True,
        )
        canal.basic_ack(delivery_tag=metodo.delivery_tag)
        devolvidas += 1
    return devolvidas


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argumentos.add_argument("--listar", action="store_true", help="só lista, sem reprocessar")
    argumentos.add_argument("--limite", type=int, default=0, help="máximo de mensagens (0 = todas)")
    opcoes = argumentos.parse_args()

    with pika.BlockingConnection(pika.URLParameters(get_settings().rabbitmq_url)) as conexao:
        canal = conexao.channel()
        canal.confirm_delivery()
        if opcoes.listar:
            print(f"{listar(canal, opcoes.limite)} mensagem(ns) listada(s).")
        else:
            print(f"{reprocessar(canal, opcoes.limite)} mensagem(ns) reprocessada(s).")


if __name__ == "__main__":
    main()
