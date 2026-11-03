"""Índices do acadêmico (RNF08): as migrações geram exatamente os índices dos models."""

import os
import re
import subprocess
import sys
from pathlib import Path

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
