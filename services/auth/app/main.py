"""Serviço auth: login, emissão de JWT, usuários e perfis (RF09, D03)."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logs import configurar_logs, registrar_middleware_de_logs
from app.core.seguranca import jwks

logger = configurar_logs("auth")

app = FastAPI(
    title="SIMPA — Auth",
    description="Autenticação, usuários e perfis de acesso.",
    root_path=get_settings().root_path,
)
registrar_middleware_de_logs(app, logger)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "auth"}


@app.get("/.well-known/jwks.json", tags=["infra"])
def chaves_publicas() -> dict:
    """Chave pública usada pelos outros serviços para validar os tokens (D15)."""
    return jwks()
