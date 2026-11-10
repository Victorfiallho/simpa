"""Fixtures dos testes entre serviços (HTTP e broker reais, ambiente `simpa-test`)."""

from __future__ import annotations

import httpx
import pytest

from tests.integration import suporte
from tests.integration.suporte import Sessao


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "interrupcao: derruba e religa um serviço do ambiente de teste. Roda sozinho, em série.",
    )


@pytest.fixture(scope="session", autouse=True)
def ambiente_pronto() -> None:
    """Falha cedo, com instrução, se o ambiente isolado não estiver de pé e ouvindo a fila."""
    try:
        resposta = httpx.get(f"{suporte.BASE_URL}/api/auth/health", timeout=5)
        resposta.raise_for_status()
    except httpx.HTTPError as erro:
        pytest.exit(
            f"Ambiente de teste fora do ar em {suporte.BASE_URL} ({erro}).\n"
            "Suba com: docker compose --env-file .env.test -p simpa-test "
            "-f compose.test.yml up -d --wait",
            returncode=2,
        )
    situacao = suporte.filas().get("analitico.recalculo-risco", {})
    if situacao.get("consumidores", 0) < 1:
        pytest.exit(
            "A fila analitico.recalculo-risco não tem consumidor: o worker não está pronto. "
            f"Estado visto: {situacao or 'fila inexistente'}",
            returncode=2,
        )


@pytest.fixture(scope="session")
def http() -> httpx.Client:
    with httpx.Client(base_url=suporte.BASE_URL, timeout=20) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def senha() -> str:
    valor = suporte.ler_env().get("DEMO_SENHA")
    assert valor, "DEMO_SENHA não encontrada em .env.test"
    return valor


@pytest.fixture(scope="session")
def admin(http: httpx.Client, senha: str) -> Sessao:
    return suporte.entrar(http, "admin@simpa.dev", senha)


@pytest.fixture(scope="session")
def coordenacao(http: httpx.Client, senha: str) -> Sessao:
    return suporte.entrar(http, "coordenacao@simpa.dev", senha)


@pytest.fixture(scope="session")
def prof_ana(http: httpx.Client, senha: str) -> Sessao:
    return suporte.entrar(http, "ana.prof@simpa.dev", senha)


@pytest.fixture(scope="session")
def prof_bruno(http: httpx.Client, senha: str) -> Sessao:
    return suporte.entrar(http, "bruno.prof@simpa.dev", senha)


@pytest.fixture
def anonimo(http: httpx.Client) -> Sessao:
    return Sessao(http, None)
