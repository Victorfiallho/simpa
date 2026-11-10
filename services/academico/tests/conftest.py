"""Fixtures dos testes do acadêmico.

Cada teste roda num SQLite em memória novo, com as mesmas constraints do Postgres
(CHECK, UNIQUE e FKs com RESTRICT). O token e o serviço auth são simulados.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import auditoria
from app.core.database import Base, get_db
from app.core.excecoes import RegraDeNegocioViolada
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from app.models import EventoOutbox
from app.services import cadastros

PROFESSOR_VALIDO = 3
OUTRO_PROFESSOR_VALIDO = 4


class EventosGravados:
    """Eventos que ficaram na outbox, como lista de (chave, dados), do mais antigo ao mais novo."""

    def __init__(self):
        self.sessoes = None  # preenchido pela fixture `cliente`

    def linhas(self) -> list[EventoOutbox]:
        with self.sessoes() as db:
            return list(
                db.scalars(select(EventoOutbox).order_by(EventoOutbox.criado_em, EventoOutbox.id))
            )

    def __iter__(self):
        return iter([(e.chave, json.loads(e.corpo)["dados"]) for e in self.linhas()])

    def __eq__(self, outro):
        return list(self) == outro

    def clear(self):
        with self.sessoes() as db:
            db.execute(delete(EventoOutbox))
            db.commit()


@pytest.fixture
def eventos():
    return EventosGravados()


@pytest.fixture
def usuario():
    """Perfil do usuário do token; o teste pode trocar `usuario.role`."""
    return UsuarioAtual(id=1, role="admin")


@pytest.fixture
def cliente(monkeypatch, eventos, usuario):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessoes = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    eventos.sessoes = sessoes

    def _db():
        db = sessoes()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _validar_professor(professor_id: int) -> None:
        if professor_id not in (PROFESSOR_VALIDO, OUTRO_PROFESSOR_VALIDO):
            raise RegraDeNegocioViolada("Professor inválido.", codigo="PROFESSOR_INVALIDO")

    monkeypatch.setattr(cadastros, "validar_professor", _validar_professor)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[usuario_atual] = lambda: usuario
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


# ---------- Atalhos para montar o cenário ----------


def criar(cliente, rota: str, corpo: dict) -> dict:
    resposta = cliente.post(rota, json=corpo)
    assert resposta.status_code == 201, resposta.json()
    return resposta.json()["dados"]


@pytest.fixture
def turma(cliente):
    return criar(
        cliente,
        "/turmas",
        {
            "codigo": "IA2-N",
            "nome": "IA 2º período",
            "curso": "Inteligência Artificial",
            "periodo_letivo": "2026.2",
            "turno": "noturno",
        },
    )


@pytest.fixture
def disciplina(cliente, turma):
    return criar(
        cliente,
        "/disciplinas",
        {
            "codigo": "EST-26",
            "nome": "Estatística Aplicada",
            "carga_horaria": 60,
            "periodo_letivo": "2026.2",
            "turma_id": turma["id"],
            "professor_id": PROFESSOR_VALIDO,
        },
    )


@pytest.fixture
def aluno(cliente, turma):
    return criar(
        cliente,
        "/alunos",
        {
            "matricula": "20260001",
            "nome_completo": "Ana Beatriz Lima",
            "cpf": "529.982.247-25",
            "email": "ana@exemplo.com",
            "curso": "Inteligência Artificial",
            "turma_id": turma["id"],
        },
    )


@pytest.fixture
def inscricao(cliente, aluno, disciplina):
    return criar(
        cliente, "/inscricoes", {"aluno_id": aluno["id"], "disciplina_id": disciplina["id"]}
    )


@pytest.fixture(autouse=True)
def auditoria_enviada(monkeypatch):
    """Registros de auditoria que iriam para o RabbitMQ; nenhum teste abre conexão."""
    enviados: list[dict] = []
    monkeypatch.setattr(auditoria, "enviar", enviados.append)
    return enviados
