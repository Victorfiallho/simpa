"""Serviço analítico: indicadores, risco, gráficos e relatórios (RF05–RF07, RF11)."""

from fastapi import Depends, FastAPI

from app.api import cenarios, rotas
from app.core.config import get_settings
from app.core.excecoes import registrar_tratadores
from app.core.logs import configurar_logs, registrar_middleware_de_logs
from app.core.seguranca import usuario_atual

logger = configurar_logs("analitico")

app = FastAPI(
    title="SIMPA — Analítico",
    description=(
        "Indicadores estatísticos, risco acadêmico e relatórios. "
        "Todas as rotas exigem o token do serviço auth (botão **Authorize**)."
    ),
    root_path=get_settings().root_path,
)
registrar_middleware_de_logs(app, logger)
registrar_tratadores(app, logger)

for roteador in (
    rotas.painel,
    rotas.indicadores,
    rotas.riscos,
    rotas.relatorio,
    cenarios.cenario,
):
    app.include_router(roteador, dependencies=[Depends(usuario_atual)])


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "analitico"}
