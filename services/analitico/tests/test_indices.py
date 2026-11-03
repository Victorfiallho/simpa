"""Índices (RNF08, desempenho): as migrações batem com os models e as consultas usam o índice.

Não substitui medir no PostgreSQL com volume: confere que os índices existem, que as migrações
geram exatamente os índices declarados e que o plano das consultas quentes não precisa ordenar.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra as tabelas no Base.metadata)
from app.core.database import Base

SERVICO = Path(__file__).resolve().parents[1]
CRIA = re.compile(r"CREATE (?:UNIQUE )?INDEX (\w+) ON (\w+) \(([^)]*)\);")
REMOVE = re.compile(r"DROP INDEX (\w+);")


def indices_das_migracoes() -> dict[str, tuple[str, tuple[str, ...]]]:
    """Gera o SQL das migrações para PostgreSQL (sem banco) e devolve os índices que sobram."""
    saida = subprocess.run(  # noqa: S603 (comando fixo, sem entrada de usuário)
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=SERVICO,
        env={**os.environ, "DATABASE_URL": "postgresql+psycopg://u:p@localhost/db"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    indices: dict[str, tuple[str, tuple[str, ...]]] = {}
    for linha in saida.splitlines():
        if criado := CRIA.match(linha):
            nome, tabela, colunas = criado.groups()
            indices[nome] = (tabela, tuple(c.strip() for c in colunas.split(",")))
        elif removido := REMOVE.match(linha):
            indices.pop(removido.group(1))
    return indices


def indices_dos_models() -> dict[str, tuple[str, tuple[str, ...]]]:
    return {
        indice.name: (tabela.name, tuple(c.name for c in indice.columns))
        for tabela in Base.metadata.sorted_tables
        for indice in tabela.indexes
    }


def test_migracoes_geram_exatamente_os_indices_dos_models():
    assert indices_das_migracoes() == indices_dos_models()


def test_migracoes_tem_uma_cabeca_so():
    saida = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "heads"],
        cwd=SERVICO,
        env={**os.environ, "DATABASE_URL": "postgresql+psycopg://u:p@localhost/db"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert len(re.findall(r"\(head\)", saida)) == 1


@pytest.fixture
def banco():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with engine.connect() as conexao:
        yield conexao
    engine.dispose()


def plano(conexao, sql: str) -> str:
    return " | ".join(str(linha[3]) for linha in conexao.execute(text(f"EXPLAIN QUERY PLAN {sql}")))


@pytest.mark.parametrize(
    ("consulta", "indice"),
    [
        # risco.ultimo_resultado e risco.historico: roda a cada evento do acadêmico
        (
            "SELECT * FROM resultado_risco WHERE inscricao_id = 1 ORDER BY id DESC LIMIT 1",
            "ix_resultado_risco_inscricao_id_id",
        ),
        # acompanhamento.do_aluno
        (
            "SELECT * FROM acompanhamento WHERE aluno_id = 1 ORDER BY data DESC, id DESC",
            "ix_acompanhamento_aluno_id_data_id",
        ),
        # apoio: pedidos do aluno, fila da coordenação por estado e histórico de um pedido
        (
            "SELECT * FROM solicitacao_apoio WHERE aluno_id = 1 ORDER BY id DESC",
            "ix_solicitacao_apoio_aluno_id_id",
        ),
        (
            "SELECT * FROM solicitacao_apoio WHERE estado = 'recebida' ORDER BY id DESC",
            "ix_solicitacao_apoio_estado_id",
        ),
        (
            "SELECT * FROM historico_apoio WHERE solicitacao_id = 1 ORDER BY id",
            "ix_historico_apoio_solicitacao_id_id",
        ),
    ],
)
def test_consulta_usa_o_indice_e_nao_ordena_a_parte(banco, consulta, indice):
    resultado = plano(banco, consulta)

    assert indice in resultado
    assert "TEMP B-TREE" not in resultado  # a ordem já vem do índice


def test_busca_de_atendimento_por_aluno_usa_a_unique(banco):
    resultado = plano(banco, "SELECT * FROM atendimento_alerta WHERE aluno_id = 1")

    # O SQLite batiza o índice da UNIQUE com nome genérico; o que importa é buscar por ele.
    assert "sqlite_autoindex_atendimento_alerta" in resultado
    assert "aluno_id=?" in resultado
