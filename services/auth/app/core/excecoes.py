"""Exceções de domínio e tratamento centralizado de erros (RF10, RNF14).

Os services levantam exceções de domínio; aqui elas viram respostas no formato padrão.
Um erro inesperado responde 500 sem stack trace (o detalhe fica só no log).
Catálogo dos códigos: docs/codigos-erro.md
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.respostas import CampoInvalido, corpo_de_erro


class ErroDeDominio(Exception):  # noqa: N818 (nome em português)
    status_http = 400
    codigo = "ERRO"

    def __init__(self, mensagem: str, codigo: str | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        if codigo:
            self.codigo = codigo


class RecursoNaoEncontrado(ErroDeDominio):
    status_http = 404
    codigo = "NAO_ENCONTRADO"


class Conflito(ErroDeDominio):
    status_http = 409
    codigo = "CONFLITO"


class RegraDeNegocioViolada(ErroDeDominio):
    status_http = 422
    codigo = "REGRA_VIOLADA"


class AcessoNegado(ErroDeDominio):
    status_http = 403
    codigo = "ACESSO_NEGADO"


class MuitasTentativas(ErroDeDominio):
    status_http = 429
    codigo = "MUITAS_TENTATIVAS"

    def __init__(self, mensagem: str, espera_segundos: int):
        super().__init__(mensagem)
        self.espera_segundos = espera_segundos


class ServicoIndisponivel(ErroDeDominio):
    status_http = 503
    codigo = "SERVICO_INDISPONIVEL"


_CODIGO_POR_STATUS = {
    401: "NAO_AUTENTICADO",
    403: "ACESSO_NEGADO",
    404: "NAO_ENCONTRADO",
    405: "METODO_NAO_PERMITIDO",
}

# Mensagens em português para as regras de validação mais comuns do Pydantic.
_MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Texto menor que o tamanho mínimo.",
    "string_too_long": "Texto maior que o tamanho máximo.",
    "greater_than": "Valor abaixo do permitido.",
    "greater_than_equal": "Valor abaixo do permitido.",
    "less_than": "Valor acima do permitido.",
    "less_than_equal": "Valor acima do permitido.",
    "int_parsing": "Informe um número inteiro.",
    "int_type": "Informe um número inteiro.",
    "decimal_parsing": "Informe um número decimal.",
    "decimal_max_places": "Use no máximo 2 casas decimais.",
    "literal_error": "Valor fora das opções permitidas.",
    "date_from_datetime_parsing": "Informe uma data no formato AAAA-MM-DD.",
    "date_parsing": "Informe uma data no formato AAAA-MM-DD.",
    "extra_forbidden": "Campo não permitido.",
    "json_invalid": "JSON inválido.",
}


def _campos(erro: RequestValidationError) -> list[CampoInvalido]:
    campos = []
    for item in erro.errors():
        local = [str(p) for p in item["loc"] if p not in ("body", "query", "path")]
        mensagem = _MENSAGENS.get(item["type"]) or str(item["msg"]).removeprefix("Value error, ")
        campos.append(
            CampoInvalido(campo=".".join(local) or "corpo", regra=item["type"], mensagem=mensagem)
        )
    return campos


def registrar_tratadores(app: FastAPI, logger: logging.Logger) -> None:
    @app.exception_handler(ErroDeDominio)
    async def _dominio(_request: Request, erro: ErroDeDominio):
        cabecalhos = (
            {"Retry-After": str(erro.espera_segundos)}
            if isinstance(erro, MuitasTentativas)
            else None
        )
        return JSONResponse(
            corpo_de_erro(erro.codigo, erro.mensagem),
            status_code=erro.status_http,
            headers=cabecalhos,
        )

    @app.exception_handler(RequestValidationError)
    async def _validacao(_request: Request, erro: RequestValidationError):
        return JSONResponse(
            corpo_de_erro("VALIDACAO", "Dados inválidos na requisição.", _campos(erro)),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, erro: StarletteHTTPException):
        codigo = _CODIGO_POR_STATUS.get(erro.status_code, "ERRO_HTTP")
        return JSONResponse(
            corpo_de_erro(codigo, str(erro.detail)),
            status_code=erro.status_code,
            headers=erro.headers,
        )

    @app.exception_handler(IntegrityError)
    async def _integridade(_request: Request, _erro: IntegrityError):
        # Rede de segurança: os services checam antes, mas o banco tem a palavra final.
        return JSONResponse(
            corpo_de_erro("CONFLITO", "O registro viola uma regra de unicidade ou integridade."),
            status_code=409,
        )

    @app.exception_handler(Exception)
    async def _inesperado(_request: Request, _erro: Exception):
        logger.exception("erro inesperado")
        return JSONResponse(
            corpo_de_erro("ERRO_INTERNO", "Erro interno. Tente novamente."), status_code=500
        )
