"""Serviço analítico: indicadores, risco, gráficos e relatórios (RF05–RF07, RF11)."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.excecoes import registrar_tratadores
from app.core.logs import configurar_logs, registrar_middleware_de_logs

logger = configurar_logs("analitico")

app = FastAPI(
    title="SIMPA — Analítico",
    description="Indicadores estatísticos, risco acadêmico, gráficos e relatórios.",
    root_path=get_settings().root_path,
)
registrar_middleware_de_logs(app, logger)
registrar_tratadores(app, logger)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "analitico"}
