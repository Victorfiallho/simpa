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
from app.services import risco
from tests.test_painel import BOM, inscricao

RUIM = [("N1", "3.00", "4"), ("N2", "2.00", "6")]


class CanalFalso:
    def __init__(self):
        self.acks, self.nacks = [], []

    def basic_ack(self, delivery_tag):
        self.acks.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacks.append((delivery_tag, requeue))


def mensagem(inscricao_id=1, **extras) -> bytes:
    return json.dumps(
        {"request_id": "req-1", "dados": {"inscricao_id": inscricao_id}, **extras}
    ).encode()


def entrega(tag=7, chave="avaliacao.alterada"):
    return SimpleNamespace(delivery_tag=tag, routing_key=chave)


@pytest.fixture
def banco(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(risco, "get_sessionmaker", lambda: fabrica)
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
def test_evento_invalido_vai_para_a_fila_de_falhas_sem_voltar_para_a_fila(corpo):
    canal = CanalFalso()

    consumidor.processar(canal, entrega(tag=9), None, corpo)

    assert (canal.acks, canal.nacks) == ([], [(9, False)])


def test_falha_no_academico_vai_para_a_fila_de_falhas(monkeypatch):
    def fora_do_ar(_id):
        raise RuntimeError("acadêmico fora do ar")

    monkeypatch.setattr(academico, "buscar_inscricao", fora_do_ar)
    canal = CanalFalso()

    consumidor.processar(canal, entrega(tag=3), None, mensagem())

    assert (canal.acks, canal.nacks) == ([], [(3, False)])
