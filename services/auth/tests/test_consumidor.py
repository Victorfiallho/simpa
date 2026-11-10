"""Consumidor de auditoria: falha vai para a fila de falhas do próprio auth (D14, RF12)."""

from types import SimpleNamespace

from app.events import consumidor


class CanalFalso:
    def __init__(self):
        self.acks, self.nacks, self.publicados = [], [], []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacks.append(delivery_tag)

    def basic_publish(self, exchange, routing_key, body, properties):
        self.publicados.append((exchange, routing_key, body, dict(properties.headers)))


def test_registro_que_nao_da_para_gravar_vai_so_para_a_fila_de_falhas_do_auth():
    canal = CanalFalso()
    metodo = SimpleNamespace(delivery_tag=5, routing_key="log.requisicao")

    consumidor.processar(canal, metodo, None, b"isto nao e json")

    assert canal.acks == [5] and canal.nacks == []
    ((exchange, chave, corpo, cabecalhos),) = canal.publicados
    # Exchange padrão + nome da fila: a exchange de falhas é `fanout` e entregaria também à fila
    # de falhas do analítico, misturando os problemas dos dois serviços.
    assert (exchange, chave, corpo) == ("", consumidor.FILA_FALHAS, b"isto nao e json")
    assert cabecalhos["x-erro"].startswith("JSONDecodeError")
