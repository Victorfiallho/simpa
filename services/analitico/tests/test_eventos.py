"""Worker do analítico: o evento recalcula o risco, com ack ou envio à fila de falhas."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clientes import academico
from app.core.database import Base
from app.core.excecoes import RecursoNaoEncontrado
from app.events import consumidor
from app.models import ResultadoRisco
from app.services import eventos as eventos_servico
from app.services import risco
from tests.test_painel import BOM, inscricao

RUIM = [("N1", "3.00", "4"), ("N2", "2.00", "6")]


class CanalFalso:
    def __init__(self):
        self.acks, self.nacks = [], []
        self.publicados: list[tuple[str, str, bytes, dict]] = []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacks.append((delivery_tag, requeue))

    def basic_publish(self, exchange, routing_key, body, properties):
        self.publicados.append((exchange, routing_key, body, dict(properties.headers or {})))


def mensagem(inscricao_id=1, **extras) -> bytes:
    return json.dumps(
        {"request_id": "req-1", "dados": {"inscricao_id": inscricao_id}, **extras}
    ).encode()


def entrega(tag=7, chave="avaliacao.alterada"):
    return SimpleNamespace(delivery_tag=tag, routing_key=chave)


def propriedades(**cabecalhos):
    return SimpleNamespace(headers=cabecalhos, message_id=None)


@pytest.fixture
def banco(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(risco, "get_sessionmaker", lambda: fabrica)
    monkeypatch.setattr(eventos_servico, "get_sessionmaker", lambda: fabrica)
    yield fabrica
    engine.dispose()


def linhas(fabrica) -> list[ResultadoRisco]:
    with fabrica() as db:
        return list(db.scalars(select(ResultadoRisco).order_by(ResultadoRisco.id)))


# ---------- Recálculo ----------


def test_evento_grava_a_classificacao_da_inscricao(banco, monkeypatch):
    monkeypatch.setattr(
        academico, "buscar_inscricao", lambda _id: inscricao(1, 1, "Ana", "EST", RUIM)
    )

    risco.recalcular_risco_da_inscricao(1)

    (linha,) = linhas(banco)
    assert (linha.inscricao_id, linha.status) == (1, "em_risco")


def test_mesmo_evento_duas_vezes_nao_duplica_a_linha(banco, monkeypatch):
    monkeypatch.setattr(
        academico, "buscar_inscricao", lambda _id: inscricao(1, 1, "Ana", "EST", RUIM)
    )

    risco.recalcular_risco_da_inscricao(1)
    risco.recalcular_risco_da_inscricao(1)

    assert len(linhas(banco)) == 1


def test_mudanca_de_classe_grava_uma_linha_nova(banco, monkeypatch):
    atual = {"notas": RUIM}
    monkeypatch.setattr(
        academico, "buscar_inscricao", lambda _id: inscricao(1, 1, "Ana", "EST", atual["notas"])
    )

    risco.recalcular_risco_da_inscricao(1)
    atual["notas"] = BOM
    risco.recalcular_risco_da_inscricao(1)

    assert [linha.status for linha in linhas(banco)] == ["em_risco", "sem_risco"]


def test_inscricao_que_nao_existe_mais_e_ignorada(banco, monkeypatch):
    def nao_existe(_id):
        raise RecursoNaoEncontrado("Inscrição não encontrada.")

    monkeypatch.setattr(academico, "buscar_inscricao", nao_existe)

    risco.recalcular_risco_da_inscricao(99)

    assert linhas(banco) == []


# ---------- Consumidor ----------


def test_evento_processado_recebe_ack(banco, monkeypatch):
    monkeypatch.setattr(
        academico, "buscar_inscricao", lambda _id: inscricao(1, 1, "Ana", "EST", RUIM)
    )
    canal = CanalFalso()

    consumidor.processar(canal, entrega(tag=7), None, mensagem())

    assert (canal.acks, canal.nacks) == ([7], [])
    assert len(linhas(banco)) == 1


@pytest.mark.parametrize(
    "corpo", [b"isto nao e json", b"{}", json.dumps({"dados": {"inscricao_id": "abc"}}).encode()]
)
def test_evento_invalido_vai_direto_para_a_fila_de_falhas_com_o_motivo(corpo):
    canal = CanalFalso()

    consumidor.processar(canal, entrega(tag=9), propriedades(), corpo)

    assert (canal.acks, canal.nacks) == ([9], [])
    ((exchange, chave, enviado, cabecalhos),) = canal.publicados
    assert (exchange, chave, enviado) == ("", consumidor.FILA_FALHAS, corpo)
    assert cabecalhos["x-erro"].startswith("evento inválido")


def falha_no_academico(monkeypatch):
    def fora_do_ar(_id):
        raise RuntimeError("acadêmico fora do ar")

    monkeypatch.setattr(academico, "buscar_inscricao", fora_do_ar)


def test_falha_passageira_volta_pela_fila_de_espera_com_o_contador(banco, monkeypatch):
    falha_no_academico(monkeypatch)
    canal = CanalFalso()

    consumidor.processar(canal, entrega(tag=3), propriedades(), mensagem())

    assert (canal.acks, canal.nacks) == ([3], [])
    ((exchange, chave, _corpo, cabecalhos),) = canal.publicados
    assert (exchange, chave) == (consumidor.EXCHANGE_ESPERA, "5")
    assert cabecalhos["x-tentativas"] == 1
    assert "acadêmico fora do ar" in cabecalhos["x-ultimo-erro"]


def test_a_espera_cresce_a_cada_tentativa(banco, monkeypatch):
    falha_no_academico(monkeypatch)
    esperas = []
    for tentativas in range(len(consumidor.ESPERAS)):
        canal = CanalFalso()
        consumidor.processar(
            canal, entrega(), propriedades(**{"x-tentativas": tentativas}), mensagem()
        )
        esperas.append(int(canal.publicados[0][1]))

    assert esperas == list(consumidor.ESPERAS) == [5, 30, 120]


def test_tentativas_esgotadas_vao_para_a_fila_de_falhas(banco, monkeypatch):
    falha_no_academico(monkeypatch)
    canal = CanalFalso()
    limite = len(consumidor.ESPERAS)

    consumidor.processar(
        canal, entrega(tag=4), propriedades(**{"x-tentativas": limite}), mensagem()
    )

    assert canal.acks == [4]
    ((exchange, _chave, _corpo, cabecalhos),) = canal.publicados
    assert (exchange, _chave) == ("", consumidor.FILA_FALHAS)
    assert cabecalhos["x-erro"].startswith("tentativas esgotadas")
    assert cabecalhos["x-tentativas"] == limite


def test_evento_repetido_e_ignorado_pelo_event_id(banco, monkeypatch):
    chamadas = []

    def buscar(_id):
        chamadas.append(_id)
        return inscricao(1, 1, "Ana", "EST", RUIM)

    monkeypatch.setattr(academico, "buscar_inscricao", buscar)
    canal = CanalFalso()
    corpo = mensagem(event_id="b3c0f4de-0000-4000-8000-000000000001")

    consumidor.processar(canal, entrega(tag=1), propriedades(), corpo)
    consumidor.processar(canal, entrega(tag=2), propriedades(), corpo)

    assert canal.acks == [1, 2]
    assert chamadas == [1], "a segunda entrega não deveria recalcular nada"
    assert canal.publicados == []
    assert len(linhas(banco)) == 1


def test_evento_que_falhou_nao_e_marcado_como_processado(banco, monkeypatch):
    """Só o que terminou conta: senão a nova tentativa seria ignorada e o risco ficaria velho."""
    falha_no_academico(monkeypatch)
    id_ = "b3c0f4de-0000-4000-8000-000000000002"

    consumidor.processar(CanalFalso(), entrega(), propriedades(), mensagem(event_id=id_))

    assert eventos_servico.ja_processado(id_) is False


def test_topologia_declara_as_filas_de_espera_ligadas_a_fila_principal():
    class Topologia:
        def __init__(self):
            self.filas, self.ligacoes, self.exchanges = {}, [], []

        def exchange_declare(self, nome, exchange_type, durable):
            self.exchanges.append((nome, exchange_type))

        def queue_declare(self, nome, durable, arguments=None):
            self.filas[nome] = arguments or {}

        def queue_bind(self, fila, exchange, routing_key=""):
            self.ligacoes.append((fila, exchange, routing_key))

    canal = Topologia()

    consumidor.declarar_topologia(canal)

    for segundos in consumidor.ESPERAS:
        argumentos = canal.filas[consumidor.fila_de_espera(segundos)]
        assert argumentos["x-message-ttl"] == segundos * 1000
        assert argumentos["x-dead-letter-exchange"] == ""
        assert argumentos["x-dead-letter-routing-key"] == consumidor.FILA
        assert (
            consumidor.fila_de_espera(segundos),
            consumidor.EXCHANGE_ESPERA,
            str(segundos),
        ) in canal.ligacoes
    assert canal.filas[consumidor.FILA]["x-dead-letter-exchange"] == consumidor.EXCHANGE_FALHAS
