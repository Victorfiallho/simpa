"""Índices do auth (RNF08, desempenho): migrações batem com os models e a trilha usa o índice.

Não substitui medir no PostgreSQL com volume: confere que os índices existem, que as migrações
geram exatamente os índices declarados e que o plano das consultas da trilha não ordena à parte.
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
AMBIENTE = {**os.environ, "DATABASE_URL": "postgresql+psycopg://u:p@localhost/db"}


def alembic(*argumentos: str) -> str:
    return subprocess.run(  # noqa: S603 (comando fixo, sem entrada de usuário)
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=SERVICO,
        env=AMBIENTE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def indices_das_migracoes() -> dict[str, tuple[str, tuple[str, ...]]]:
    """Gera o SQL das migrações para PostgreSQL (sem banco) e devolve os índices que sobram."""
    indices: dict[str, tuple[str, tuple[str, ...]]] = {}
    for linha in alembic("upgrade", "head", "--sql").splitlines():
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
    assert len(re.findall(r"\(head\)", alembic("heads"))) == 1


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
        (
            "SELECT * FROM log_requisicao WHERE usuario_id = 7 ORDER BY timestamp DESC LIMIT 20",
            "ix_log_requisicao_usuario_id_timestamp",
        ),
        (
            "SELECT * FROM log_requisicao WHERE status_http = 500 ORDER BY timestamp DESC LIMIT 20",
            "ix_log_requisicao_status_http_timestamp",
        ),
        (
            "SELECT * FROM log_requisicao ORDER BY timestamp DESC LIMIT 20",
            "ix_log_requisicao_timestamp",
        ),
    ],
)
def test_trilha_usa_o_indice_e_nao_ordena_a_parte(banco, consulta, indice):
    resultado = plano(banco, consulta)

    assert indice in resultado
    assert "TEMP B-TREE" not in resultado  # a ordem já vem do índice
