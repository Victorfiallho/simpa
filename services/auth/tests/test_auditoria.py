"""Auditoria no auth: o worker grava o registro e o login nunca expõe a senha (RF12, RNF04)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auditoria import CAMPOS
from app.core.database import Base
from app.models import LogRequisicao
from app.services.auditoria import gravar_registro
from tests.test_usuarios import SENHA, cliente, entrar, sessoes  # noqa: F401


def registro(**alteracoes) -> dict:
    return {
        "correlation_id": "req-1",
        "usuario_id": 7,
        "rota": "/turmas",
        "metodo_http": "GET",
        "status_http": 200,
        "ip_origem": "10.0.0.7",
        "tempo_resposta_ms": 12,
        "timestamp": datetime.now(UTC).isoformat(),
    } | alteracoes


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as sessao:
        yield sessao
    engine.dispose()


def test_grava_o_registro(db):
    assert gravar_registro(db, registro()) is True

    gravado = db.scalar(select(LogRequisicao))
    assert (gravado.usuario_id, gravado.rota, gravado.status_http) == (7, "/turmas", 200)
    assert gravado.tempo_resposta_ms == 12


def test_mensagem_repetida_nao_duplica(db):
    gravar_registro(db, registro())

    assert gravar_registro(db, registro()) is False
    assert len(db.scalars(select(LogRequisicao)).all()) == 1


def test_campos_extras_da_mensagem_sao_descartados(db):
    gravar_registro(db, registro(senha="segredo", authorization="Bearer x", cpf="52998224725"))

    gravado = db.scalar(select(LogRequisicao))
    assert "segredo" not in str(vars(gravado))
    assert not hasattr(gravado, "cpf")


def test_registro_invalido_e_recusado(db):
    with pytest.raises(ValueError):
        gravar_registro(db, registro(status_http=999))


def test_login_e_registrado_sem_senha_nem_corpo(cliente, auditoria_enviada):  # noqa: F811
    entrar(cliente, "admin@simpa.dev", SENHA)

    enviado = auditoria_enviada[-1]
    assert set(enviado) == set(CAMPOS)
    assert enviado["rota"] == "/login"
    assert enviado["metodo_http"] == "POST"
    assert enviado["usuario_id"] is None
    assert SENHA not in str(enviado)
    assert "admin@simpa.dev" not in str(enviado)
