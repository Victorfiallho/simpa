"""Serviço auth: login, emissão de JWT, usuários e perfis (RF09, D03)."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db, get_sessionmaker
from app.core.excecoes import RecursoNaoEncontrado, registrar_tratadores
from app.core.logs import configurar_logs, registrar_middleware_de_logs
from app.core.paginacao import Paginacao, paginacao
from app.core.respostas import Resposta, RespostaPaginada, resposta, resposta_paginada
from app.core.seguranca import exigir_roles, jwks
from app.models import Usuario
from app.schemas import Login, RegistroAuditoria, Token, UsuarioResumo
from app.services import auditoria, usuarios

logger = configurar_logs("auth")
Sessao = Annotated[Session, Depends(get_db)]
Pagina = Annotated[Paginacao, Depends(paginacao)]


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    settings = get_settings()
    if settings.usuarios_demo:
        if not settings.demo_senha:
            raise RuntimeError("USUARIOS_DEMO=true exige DEMO_SENHA no .env")
        with get_sessionmaker()() as db:
            usuarios.garantir_usuarios_demo(db, settings.demo_senha, settings.demo_aluno_id)
    yield


app = FastAPI(
    title="SIMPA — Auth",
    description="Autenticação, usuários e perfis de acesso.",
    root_path=get_settings().root_path,
    lifespan=ciclo_de_vida,
)
registrar_middleware_de_logs(app, logger)
registrar_tratadores(app, logger)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "servico": "auth"}


@app.get("/.well-known/jwks.json", tags=["infra"])
def chaves_publicas() -> dict:
    """Chave pública usada pelos outros serviços para validar os tokens (D15)."""
    return jwks()


@app.post(
    "/login",
    response_model=Resposta[Token],
    tags=["Autenticação"],
    responses={401: {"description": "E-mail ou senha inválidos"}},
)
def login(dados: Login, db: Sessao):
    """Troca e-mail e senha por um token. Use o `access_token` no botão **Authorize**."""
    token = usuarios.autenticar(db, dados.email, dados.senha)
    if token is None:
        # Mensagem genérica: não revela se o erro foi no e-mail ou na senha (RF09 CA01).
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    return Resposta[Token](dados=token, mensagem="Login realizado.")


@app.get(
    "/auditoria",
    response_model=RespostaPaginada[RegistroAuditoria],
    tags=["Auditoria"],
    dependencies=[Depends(exigir_roles("admin", "coordenador"))],
)
def listar_auditoria(
    db: Sessao,
    pagina: Pagina,
    usuario_id: int | None = None,
    status_http: Annotated[int | None, Query(ge=100, le=599)] = None,
    classe_status: Annotated[
        int | None, Query(ge=2, le=5, description="2, 4 ou 5 para 2xx, 4xx ou 5xx")
    ] = None,
    metodo_http: Annotated[str | None, Query(max_length=10)] = None,
    busca: Annotated[
        str | None,
        Query(min_length=2, max_length=60, description="Parte da rota ou do correlation id"),
    ] = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
):
    """Trilha de auditoria das requisições (RF12). Só admin e coordenador. Mais recentes primeiro
    com `ordenar_por=timestamp&ordem=desc`."""
    itens, total = auditoria.listar_registros(
        db,
        pagina,
        usuario_id=usuario_id,
        status_http=status_http,
        classe_status=classe_status,
        metodo_http=metodo_http,
        busca=busca,
        desde=desde,
        ate=ate,
    )
    return resposta_paginada(RegistroAuditoria, itens, total, pagina.pagina, pagina.limite)


# ---------- Rotas internas (bloqueadas no gateway) ----------


@app.get(
    "/internal/usuarios/{usuario_id}",
    response_model=Resposta[UsuarioResumo],
    include_in_schema=False,
)
def usuario_interno(usuario_id: int, db: Sessao):
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    return resposta(UsuarioResumo, usuario)


@app.get(
    "/internal/usuarios", response_model=Resposta[list[UsuarioResumo]], include_in_schema=False
)
def usuarios_internos(db: Sessao, role: Literal["admin", "coordenador", "professor"] | None = None):
    consulta = select(Usuario).order_by(Usuario.id)
    if role:
        consulta = consulta.where(Usuario.role == role)
    lista = [UsuarioResumo.model_validate(u) for u in db.scalars(consulta)]
    return Resposta[list[UsuarioResumo]](dados=lista)
