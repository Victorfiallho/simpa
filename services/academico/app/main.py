"""Serviço acadêmico: turmas, disciplinas, alunos, inscrições, notas e frequência (RF01–RF04)."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logs import configurar_logs, registrar_middleware_de_logs

logger = configurar_logs("academico")

app = FastAPI(
    title="SIMPA — Acadêmico",
    description="Cadastros acadêmicos, lançamento de notas e frequência.",
    root_path=get_settings().root_path,
)
registrar_middleware_de_logs(app, logger)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "academico"}
