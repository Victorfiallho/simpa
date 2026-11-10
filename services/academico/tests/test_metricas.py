"""Métricas do despachante da outbox (etapa 6): contadores por resultado e medidores da outbox."""

from datetime import UTC, datetime, timedelta

import pytest
from pika.exceptions import NackError, UnroutableError
from prometheus_client import REGISTRY
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.events import despachante, metricas
from app.events.outbox import registrar_evento
from app.models import EventoOutbox


class CanalFalso:
    def __init__(self, erro=None):
        self.erro = erro

    def basic_publish(self, **_argumentos):
        if self.erro is not None:
            raise self.erro


@pytest.fixture
def fabrica():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


def valor(nome: str, **rotulos) -> float:
    return REGISTRY.get_sample_value(nome, rotulos) or 0.0


def gravar(fabrica, criado_em=None) -> str:
    with fabrica() as db:
        evento = registrar_evento(db, "avaliacao.alterada", {"inscricao_id": 1})
        if criado_em:
            evento.criado_em = criado_em
        db.commit()
        return evento.id


@pytest.mark.parametrize(
    ("erro", "resultado"),
    [(None, "ok"), (UnroutableError([]), "sem_destino"), (NackError([]), "recusado")],
)
def test_cada_tentativa_de_publicacao_conta_no_seu_resultado(fabrica, erro, resultado):
    gravar(fabrica)
    antes = {r: valor("academico_despachante_publicacoes_total", resultado=r) for r in (
        "ok", "sem_destino", "recusado")}  # fmt: skip

    despachante.despachar_pendentes(fabrica, CanalFalso(erro))

    for r, anterior in antes.items():
        esperado = anterior + (1 if r == resultado else 0)
        assert valor("academico_despachante_publicacoes_total", resultado=r) == esperado


def test_as_series_existem_desde_o_inicio_mesmo_sem_nenhum_evento():
    """Sem a série, `increase()` e a detecção de série ausente dariam um falso alarme."""
    for r in metricas.RESULTADOS_PUBLICACAO:
        assert (
            REGISTRY.get_sample_value("academico_despachante_publicacoes_total", {"resultado": r})
            is not None
        )
    for m in metricas.MOTIVOS_RECONEXAO:
        assert (
            REGISTRY.get_sample_value("academico_despachante_reconexoes_total", {"motivo": m})
            is not None
        )


def test_medidores_da_outbox_mostram_quantos_esperam_e_ha_quanto_tempo(fabrica):
    agora = datetime.now(UTC)
    gravar(fabrica, criado_em=agora - timedelta(seconds=90))
    gravar(fabrica, criado_em=agora - timedelta(seconds=10))

    with fabrica() as db:
        metricas.atualizar_outbox(db, agora)

    assert valor("academico_outbox_eventos_pendentes") == 2
    assert valor("academico_outbox_idade_evento_mais_antigo_segundos") == pytest.approx(90, abs=1)


def test_outbox_vazia_ou_toda_enviada_zera_os_medidores(fabrica):
    gravar(fabrica)
    despachante.despachar_pendentes(fabrica, CanalFalso())

    with fabrica() as db:
        metricas.atualizar_outbox(db)

    assert valor("academico_outbox_eventos_pendentes") == 0
    assert valor("academico_outbox_idade_evento_mais_antigo_segundos") == 0


def test_evento_que_espera_a_proxima_tentativa_continua_contando_como_pendente(fabrica):
    """O atraso antes do broker conta mesmo quando o evento está em espera progressiva."""
    gravar(fabrica, criado_em=datetime.now(UTC) - timedelta(seconds=200))
    despachante.despachar_pendentes(fabrica, CanalFalso(UnroutableError([])))

    with fabrica() as db:
        metricas.atualizar_outbox(db)
        espera = db.query(EventoOutbox).one().proxima_tentativa_em

    assert espera.replace(tzinfo=UTC) > datetime.now(UTC)
    assert valor("academico_outbox_eventos_pendentes") == 1
    assert valor("academico_outbox_idade_evento_mais_antigo_segundos") >= 199


def test_atualizar_metricas_nao_levanta_se_o_banco_falhar():
    """Roda numa thread própria: um erro aqui não pode derrubá-la e congelar as métricas."""

    class SessaoQuebrada:
        def __enter__(self):
            raise RuntimeError("banco fora do ar")

        def __exit__(self, *_):
            return False

    assert despachante.atualizar_metricas(lambda: SessaoQuebrada()) is False


def test_atualizar_metricas_devolve_true_quando_funciona(fabrica):
    assert despachante.atualizar_metricas(fabrica) is True
