"""Despachante da outbox: confirmação do broker, mensagem sem destino e entrega repetida (D14)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from pika.exceptions import AMQPConnectionError, NackError, UnroutableError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.events import despachante
from app.events.outbox import registrar_evento
from app.models import EventoOutbox


class CanalFalso:
    """Canal com publisher confirm: `basic_publish` só volta depois da confirmação do broker."""

    def __init__(self, erro=None):
        self.erro = erro
        self.publicados: list[dict] = []

    def basic_publish(self, exchange, routing_key, body, properties, mandatory):
        if self.erro is not None:
            raise self.erro
        self.publicados.append(
            {
                "exchange": exchange,
                "chave": routing_key,
                "envelope": json.loads(body),
                "message_id": properties.message_id,
                "persistente": properties.delivery_mode == 2,
                "mandatory": mandatory,
            }
        )


@pytest.fixture
def fabrica():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


def gravar(fabrica, chave="avaliacao.alterada", inscricao_id=1, criado_em=None) -> str:
    with fabrica() as db:
        evento = registrar_evento(db, chave, {"inscricao_id": inscricao_id})
        if criado_em:
            evento.criado_em = criado_em
        db.commit()
        return evento.id


def linhas(fabrica) -> list[EventoOutbox]:
    with fabrica() as db:
        return list(db.scalars(select(EventoOutbox).order_by(EventoOutbox.criado_em)))


def test_publica_na_ordem_com_confirmacao_e_marca_como_enviado(fabrica):
    agora = datetime.now(UTC)
    segundo = gravar(fabrica, "frequencia.alterada", 2, criado_em=agora)
    primeiro = gravar(fabrica, "avaliacao.alterada", 1, criado_em=agora - timedelta(seconds=5))
    canal = CanalFalso()

    assert despachante.despachar_pendentes(fabrica, canal) == 2

    assert [p["message_id"] for p in canal.publicados] == [primeiro, segundo]
    assert all(p["exchange"] == "simpa.eventos" and p["persistente"] for p in canal.publicados)
    assert all(p["mandatory"] for p in canal.publicados), (
        "sem mandatory, o broker descarta em silêncio"
    )
    assert [p["envelope"]["event_id"] for p in canal.publicados] == [primeiro, segundo]
    assert all(e.enviado_em is not None and e.tentativas == 0 for e in linhas(fabrica))


def test_evento_ja_enviado_nao_e_publicado_de_novo(fabrica):
    gravar(fabrica)
    canal = CanalFalso()

    despachante.despachar_pendentes(fabrica, canal)
    despachante.despachar_pendentes(fabrica, canal)

    assert len(canal.publicados) == 1


@pytest.mark.parametrize("erro", [UnroutableError([]), NackError([])])
def test_sem_destino_ou_recusado_continua_pendente_com_espera_progressiva(fabrica, erro):
    id_ = gravar(fabrica)
    canal = CanalFalso(erro=erro)

    assert despachante.despachar_pendentes(fabrica, canal) == 1

    (evento,) = linhas(fabrica)
    assert evento.id == id_
    assert evento.enviado_em is None
    assert evento.tentativas == 1
    assert type(erro).__name__ in evento.ultimo_erro
    assert evento.proxima_tentativa_em.replace(tzinfo=UTC) > datetime.now(UTC)

    # Antes de vencer a espera, não há nova tentativa.
    canal.erro = None
    assert despachante.despachar_pendentes(fabrica, canal) == 0
    assert canal.publicados == []

    # Vencida a espera, e agora com destino, o evento sai e o erro some.
    with fabrica() as db:
        db.get(EventoOutbox, id_).proxima_tentativa_em = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert despachante.despachar_pendentes(fabrica, canal) == 1
    (evento,) = linhas(fabrica)
    assert evento.enviado_em is not None and evento.ultimo_erro is None
    assert [p["message_id"] for p in canal.publicados] == [id_]


def test_espera_cresce_e_tem_teto():
    esperas = [despachante.espera_progressiva(n).total_seconds() for n in (1, 2, 3, 4)]
    assert esperas == [2, 4, 8, 16]
    assert despachante.espera_progressiva(50).total_seconds() == despachante.ESPERA_MAXIMA_SEGUNDOS


def test_broker_fora_do_ar_nao_marca_nada_e_o_evento_espera(fabrica):
    gravar(fabrica)
    canal = CanalFalso(erro=AMQPConnectionError("conexão recusada"))

    with pytest.raises(AMQPConnectionError):
        despachante.despachar_pendentes(fabrica, canal)

    (evento,) = linhas(fabrica)
    assert evento.enviado_em is None
    assert evento.tentativas == 0, "queda do broker não é culpa do evento"

    # O broker volta: o mesmo evento sai, sem ninguém ter lançado nada de novo.
    volta = CanalFalso()
    assert despachante.despachar_pendentes(fabrica, volta) == 1
    assert len(volta.publicados) == 1


def test_queda_entre_o_envio_e_a_marcacao_reenvia_o_mesmo_evento(fabrica):
    """Entrega "pelo menos uma vez": o id é o mesmo, e o consumidor ignora a repetição por ele."""
    id_ = gravar(fabrica)
    canal = CanalFalso()

    with fabrica() as db:

        def commit_que_falha():
            raise OperationalError("UPDATE", {}, Exception("conexão perdida"))

        db.commit = commit_que_falha
        with pytest.raises(OperationalError):
            despachante.despachar_um(db, canal, datetime.now(UTC))
        db.rollback()

    assert linhas(fabrica)[0].enviado_em is None  # a marcação não aconteceu

    despachante.despachar_pendentes(fabrica, canal)

    assert [p["message_id"] for p in canal.publicados] == [id_, id_]
    assert linhas(fabrica)[0].enviado_em is not None


class _Sair(BaseException):
    """Interrompe o laço infinito do `main` depois que o que interessa foi observado."""


def test_nome_do_broker_que_nao_resolve_faz_reconectar_em_vez_de_derrubar_o_processo(monkeypatch):
    """Com o contêiner do RabbitMQ parado, o nome dele some da rede do Docker.

    O pika levanta `socket.gaierror` (um `OSError`, não um `AMQPError`). O despachante tem de tratar
    como broker indisponível e tentar de novo, em vez de morrer e depender do restart do Docker.
    """
    import socket
    from types import SimpleNamespace

    from prometheus_client import REGISTRY

    tentativas = []

    def conectar(_parametros):
        tentativas.append(1)
        if len(tentativas) == 1:
            raise socket.gaierror(-2, "Name or service not known")
        raise _Sair

    monkeypatch.setattr(despachante.pika, "BlockingConnection", conectar)
    monkeypatch.setattr(despachante.time, "sleep", lambda _segundos: None)
    monkeypatch.setattr(despachante, "get_sessionmaker", lambda: None)
    monkeypatch.setattr(despachante, "configurar_logs", lambda _nome: None)
    monkeypatch.setattr(despachante.metricas, "iniciar_servidor", lambda _porta: None)
    monkeypatch.setattr(
        despachante.threading, "Thread", lambda **_k: SimpleNamespace(start=lambda: None)
    )
    rotulo = {"motivo": "broker"}
    antes = REGISTRY.get_sample_value("academico_despachante_reconexoes_total", rotulo)

    with pytest.raises(_Sair):
        despachante.main()

    assert len(tentativas) == 2, "depois da falha de nome, tentou conectar de novo"
    assert REGISTRY.get_sample_value("academico_despachante_reconexoes_total", rotulo) == antes + 1
