"""Cabeçalhos de segurança do gateway e a CSP da aplicação (defesa em profundidade contra XSS)."""

import httpx
import pytest

from tests.integration import suporte

COMUNS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=suporte.BASE_URL, timeout=15) as cliente:
        yield cliente


@pytest.mark.parametrize(
    "caminho", ["/", "/api/auth/health", "/api/academico/health", "/nao-existe"]
)
def test_cabecalhos_comuns_em_todas_as_respostas(http, caminho):
    resposta = http.get(caminho)
    for nome, valor in COMUNS.items():
        assert resposta.headers.get(nome) == valor, f"{caminho}: {nome} ausente ou diferente"
    assert "camera=()" in resposta.headers.get("permissions-policy", "")


def test_csp_da_pagina_restringe_scripts_e_embutir(http):
    csp = http.get("/").headers.get("content-security-policy", "")
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "'unsafe-eval'" not in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "connect-src 'self'" in csp


def test_csp_tambem_vale_para_rotas_do_react_router(http):
    # Qualquer caminho que não é arquivo devolve o index.html, e precisa da mesma política.
    assert "script-src 'self'" in http.get("/analises").headers.get("content-security-policy", "")


def test_api_nao_recebe_csp_da_pagina(http):
    # O Swagger (/api/*/docs) usa scripts de CDN; a CSP da página os quebraria.
    assert "content-security-policy" not in http.get("/api/auth/health").headers
