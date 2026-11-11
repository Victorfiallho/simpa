"""Comando de reprocessamento da fila de falhas (D14): listar não consome; reprocessar devolve."""

import json
from types import SimpleNamespace

from app.comandos import reprocessar_falhas as comando
from app.events.consumidor import FILA, FILA_FALHAS


class FilaFalsa:
    """Fila com semântica de entrega do RabbitMQ: mensagem lida e não confirmada fica 'em voo'."""

    def __init__(self, mensagens):
        self.na_fila = list(mensagens)
        self.em_voo: dict[int, tuple] = {}
        self.publicados = []
        self.proxima_tag = 1

    def queue_declare(self, fila, passive):
        assert fila == FILA_FALHAS and passive
        return SimpleNamespace(method=SimpleNamespace(message_count=len(self.na_fila)))

    def basic_get(self, fila, auto_ack):
        if not self.na_fila:
            return None, None, None
        corpo, cabecalhos = self.na_fila.pop(0)
        tag = self.proxima_tag
        self.proxima_tag += 1
        self.em_voo[tag] = (corpo, cabecalhos)
        propriedades = SimpleNamespace(headers=dict(cabecalhos), message_id="m")
        return SimpleNamespace(delivery_tag=tag), propriedades, corpo

    def basic_ack(self, delivery_tag):
        self.em_voo.pop(delivery_tag)

    def basic_nack(self, delivery_tag, multiple, requeue):
        assert multiple and requeue
        devolvidas = [t for t in sorted(self.em_voo) if t <= delivery_tag]
        self.na_fila.extend(self.em_voo.pop(t) for t in devolvidas)

    def basic_publish(self, exchange, routing_key, body, properties, mandatory):
        self.publicados.append((exchange, routing_key, body, dict(properties.headers)))


def mensagem(n):
    corpo = json.dumps({"event_id": f"id-{n}"}).encode()
    return corpo, {"x-erro": "evento inválido", "x-tentativas": 3, "x-chave": "avaliacao.alterada"}


def test_listar_mostra_cada_mensagem_uma_vez_e_nao_consome_nenhuma(capsys):
    fila = FilaFalsa([mensagem(1), mensagem(2), mensagem(3)])

    assert comando.listar(fila, limite=0) == 3

    saida = capsys.readouterr().out.splitlines()
    assert [linha.split()[0] for linha in saida] == [
        "event_id=id-1",
        "event_id=id-2",
        "event_id=id-3",
    ]
    assert "erro=evento inválido" in saida[0]
    assert len(fila.na_fila) == 3 and fila.em_voo == {}, "listar deixou a fila como estava"


def test_reprocessar_devolve_cada_mensagem_uma_vez_sem_os_cabecalhos_de_falha():
    fila = FilaFalsa([mensagem(1), mensagem(2)])

    assert comando.reprocessar(fila, limite=0) == 2

    assert [p[:2] for p in fila.publicados] == [("", FILA), ("", FILA)]
    cabecalhos = fila.publicados[0][3]
    assert cabecalhos == {"x-chave": "avaliacao.alterada", "x-reprocessado": True}
    assert fila.na_fila == [] and fila.em_voo == {}


def test_reprocessar_respeita_o_limite():
    fila = FilaFalsa([mensagem(1), mensagem(2), mensagem(3)])

    assert comando.reprocessar(fila, limite=2) == 2

    assert len(fila.publicados) == 2 and len(fila.na_fila) == 1


def test_fila_vazia_nao_faz_nada(capsys):
    fila = FilaFalsa([])

    assert comando.listar(fila, limite=0) == 0
    assert comando.reprocessar(fila, limite=0) == 0
    assert fila.publicados == []
