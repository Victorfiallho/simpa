"""Serviço acadêmico: turmas, disciplinas, alunos, inscrições, notas e frequência (RF01–RF04)."""

from fastapi import Depends, FastAPI

from app.api import cadastros, lancamentos
from app.api.interna import interna
from app.core.config import get_settings
from app.core.excecoes import registrar_tratadores
from app.core.logs import configurar_logs, registrar_middleware_de_logs
from app.core.seguranca import usuario_atual

logger = configurar_logs("academico")

app = FastAPI(
    title="SIMPA — Acadêmico",
    description=(
        "Cadastros acadêmicos, lançamento de notas e frequência. "
        "Todas as rotas exigem o token do serviço auth (botão **Authorize**)."
    ),
    root_path=get_settings().root_path,
)
registrar_middleware_de_logs(app, logger)
registrar_tratadores(app, logger)

autenticado = [Depends(usuario_atual)]
for roteador in (
    cadastros.turmas,
    cadastros.disciplinas,
    cadastros.alunos,
    lancamentos.inscricoes,
    lancamentos.avaliacoes,
    lancamentos.frequencias,
):
    app.include_router(roteador, dependencies=autenticado)
app.include_router(interna)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "academico"}
