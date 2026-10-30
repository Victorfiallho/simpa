"""Validação do JWT emitido pelo serviço auth (RF09, D15).

Este serviço não tem a chave privada: só confere a assinatura com a chave pública
publicada pelo auth em /.well-known/jwks.json (buscada uma vez e guardada em cache).

Uso nas rotas:  usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]
"""

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.excecoes import AcessoNegado
from app.core.logs import identificar_usuario

ALGORITMO = "RS256"
EMISSOR = "simpa-auth"
ROLES = {"admin", "coordenador", "professor"}

_bearer = HTTPBearer(auto_error=False)


class UsuarioAtual(BaseModel):
    id: int
    role: str
    nome: str | None = None


@lru_cache
def _cliente_jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(get_settings().auth_jwks_url, cache_keys=True)


def _decodificar(credenciais: HTTPAuthorizationCredentials | None) -> tuple[dict, HTTPException]:
    """Valida a assinatura do token. Devolve o conteúdo e o erro 401 genérico (RF09 CA01)."""
    nao_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise nao_autenticado

    try:
        chave = _cliente_jwks().get_signing_key_from_jwt(credenciais.credentials)
        dados = jwt.decode(
            credenciais.credentials,
            chave.key,
            algorithms=[ALGORITMO],
            issuer=EMISSOR,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.PyJWTError as erro:
        raise nao_autenticado from erro
    return dados, nao_autenticado


def usuario_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UsuarioAtual:
    """Devolve o usuário (admin, coordenador ou professor) ou responde 401 genérico."""
    dados, nao_autenticado = _decodificar(credenciais)
    if dados.get("role") not in ROLES or not str(dados["sub"]).isdigit():
        raise nao_autenticado

    identificar_usuario(int(dados["sub"]))
    return UsuarioAtual(id=int(dados["sub"]), role=dados["role"], nome=dados.get("nome"))


class AlunoAtual(BaseModel):
    """O aluno logado: o id do usuário no auth e o do cadastro dele no acadêmico."""

    id: int
    aluno_id: int
    nome: str | None = None


def aluno_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AlunoAtual:
    """Só aceita token do perfil aluno, com `aluno_id`. As rotas dos outros perfis seguem
    usando `usuario_atual`, que recusa este token."""
    dados, nao_autenticado = _decodificar(credenciais)
    aluno_id = dados.get("aluno_id")
    if (
        dados.get("role") != "aluno"
        or not str(dados["sub"]).isdigit()
        or not isinstance(aluno_id, int)
        or isinstance(aluno_id, bool)
    ):
        raise nao_autenticado
    return AlunoAtual(id=int(dados["sub"]), aluno_id=aluno_id, nome=dados.get("nome"))


def exigir_roles(*permitidos: str) -> Callable[[UsuarioAtual], UsuarioAtual]:
    """Dependência que responde 403 se o perfil do token não estiver em `permitidos` (D03).

    Uso:  @router.post("", dependencies=[Depends(exigir_roles("admin", "coordenador"))])
    """
    desconhecidos = set(permitidos) - ROLES
    if desconhecidos:
        raise ValueError(f"Perfis desconhecidos: {sorted(desconhecidos)}")

    def verificar(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
        if usuario.role not in permitidos:
            raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
        return usuario

    return verificar
