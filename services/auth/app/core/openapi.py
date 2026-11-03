"""Documenta no OpenAPI as respostas de erro comuns a todas as rotas (RNF14).

Os services levantam exceções de domínio e o tratador central as converte para o envelope
padrão (`core/excecoes.py`). Em vez de repetir `responses={...}` em cada rota, o esquema
gerado pelo FastAPI recebe aqui 400, 401, 403, 404 e 500, todos no formato `ErroPadrao`, e o 422
(que o FastAPI descreveria com o formato dele) passa a apontar para o mesmo envelope.
"""

from typing import Any

from fastapi import FastAPI

from app.core.respostas import Resposta

ERROS = {
    "400": "Requisição inválida, por exemplo parâmetro de query repetido (`PARAMETRO_REPETIDO`).",
    "401": "Não autenticado: token ausente, inválido ou expirado (`NAO_AUTENTICADO`).",
    "403": "O perfil do token não pode executar esta ação (`ACESSO_NEGADO`).",
    "404": "O recurso pedido não existe (`NAO_ENCONTRADO`).",
    "422": "Dados fora do formato ou regra de negócio violada; veja `erro.campos` (`VALIDACAO`).",
    "429": "Muitas tentativas de login seguidas; aguarde o `Retry-After` (`MUITAS_TENTATIVAS`).",
    "500": "Erro interno, sem detalhes na resposta; o `X-Request-ID` leva ao log (`ERRO_INTERNO`).",
}
ABERTAS = {"/health", "/.well-known/jwks.json"}  # sem token: não têm 401 nem 403
SO_COM_LOGIN_ERRADO = {"/login"}  # tem 401 (credencial errada), mas não 403
EXTRAS = {"/login": {"429"}}  # respostas só de uma rota


def _resposta_de_erro(descricao: str) -> dict[str, Any]:
    return {
        "description": descricao,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErroPadrao"}}},
    }


def _acrescentar(esquema: dict[str, Any]) -> None:
    modelo = Resposta[None].model_json_schema(ref_template="#/components/schemas/{model}")
    componentes = esquema.setdefault("components", {}).setdefault("schemas", {})
    componentes.update(modelo.pop("$defs", {}))
    componentes["ErroPadrao"] = modelo
    componentes.pop("HTTPValidationError", None)
    componentes.pop("ValidationError", None)

    for caminho, operacoes in esquema.get("paths", {}).items():
        for metodo, operacao in operacoes.items():
            if metodo not in {"get", "post", "put", "patch", "delete"}:
                continue
            codigos = {"400", "500"}
            if caminho not in ABERTAS:
                codigos |= {"401"}
                if caminho not in SO_COM_LOGIN_ERRADO:
                    codigos |= {"403"}
            codigos |= EXTRAS.get(caminho, set())
            if "{" in caminho:
                codigos.add("404")
            if "422" in operacao.get("responses", {}) or metodo in {"post", "put", "patch"}:
                codigos.add("422")
            for codigo in codigos:
                operacao.setdefault("responses", {})[codigo] = _resposta_de_erro(ERROS[codigo])


def documentar_erros(app: FastAPI) -> None:
    """Faz `app.openapi()` devolver o esquema com as respostas de erro padrão."""
    original = app.openapi

    def openapi() -> dict[str, Any]:
        primeira_vez = app.openapi_schema is None
        esquema = original()
        if primeira_vez:
            _acrescentar(esquema)
        return esquema

    app.openapi = openapi  # type: ignore[method-assign]
