"""Logs em JSON na saída padrão, sempre com o X-Request-ID gerado pelo gateway (RF12).

Com o mesmo request_id em todos os serviços, dá para seguir uma requisição de ponta a
ponta com `docker compose logs | grep <request_id>`.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request

request_id_atual: ContextVar[str] = ContextVar("request_id", default="-")


class _FormatoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "momento": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "nivel": record.levelname,
            "origem": record.name,
            "request_id": request_id_atual.get(),
            "mensagem": record.getMessage(),
        }
        dados.update(getattr(record, "dados", {}))
        if record.exc_info:
            dados["erro"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


def configurar_logs(servico: str) -> logging.Logger:
    """Configura o logger raiz do serviço. Os módulos usam logging.getLogger(f"{servico}.x")."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_FormatoJson())
    logger = logging.getLogger(servico)
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def registrar_middleware_de_logs(app: FastAPI, logger: logging.Logger) -> None:
    """Registra uma linha de log por requisição e devolve o X-Request-ID na resposta.

    Nunca registra corpo, cabeçalho de autorização ou query string (RNF04).
    """

    @app.middleware("http")
    async def _log_da_requisicao(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_atual.set(request_id)
        inicio = time.perf_counter()
        status_http = 500
        try:
            resposta = await call_next(request)
            status_http = resposta.status_code
            resposta.headers["X-Request-ID"] = request_id
            return resposta
        finally:
            # O healthcheck do Docker chama /health a cada 10 s; registrar só poluiria o log.
            if request.url.path != "/health":
                logger.info(
                    "requisicao",
                    extra={
                        "dados": {
                            "metodo": request.method,
                            "rota": request.url.path,
                            "status_http": status_http,
                            "tempo_ms": round((time.perf_counter() - inicio) * 1000),
                        }
                    },
                )
            request_id_atual.reset(token)
