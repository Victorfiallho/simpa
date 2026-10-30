"""Quem está logado, nas rotas protegidas do próprio auth (RF09).

O auth tem a chave privada, então valida o token com a chave pública dele mesmo, sem passar
pelo JWKS. Qualquer perfil (inclusive aluno) entra; cada rota decide o que o perfil pode.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.seguranca import ALGORITMO, EMISSOR, chave_privada

_ROLES = {"admin", "coordenador", "professor", "aluno"}
_bearer = HTTPBearer(auto_error=False)


class UsuarioLogado(BaseModel):
    id: int
    role: str
    nome: str | None = None


def usuario_logado(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UsuarioLogado:
    """Valida o token ou responde 401 com mensagem genérica (RF09 CA01)."""
    nao_autenticado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise nao_autenticado
    try:
        dados = jwt.decode(
            credenciais.credentials,
            chave_privada().public_key(),
            algorithms=[ALGORITMO],
            issuer=EMISSOR,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.PyJWTError as erro:
        raise nao_autenticado from erro
    if dados.get("role") not in _ROLES or not str(dados["sub"]).isdigit():
        raise nao_autenticado
    return UsuarioLogado(id=int(dados["sub"]), role=dados["role"], nome=dados.get("nome"))
