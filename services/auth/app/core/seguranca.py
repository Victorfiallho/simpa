"""Emissão de tokens JWT (RF09, D15).

O auth é o único serviço com a chave privada. Os outros validam os tokens com a chave
pública, publicada em /.well-known/jwks.json. Assim, nenhum outro serviço consegue
emitir um token, mesmo que seja comprometido.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.excecoes import AcessoNegado
from app.core.logs import identificar_usuario

ALGORITMO = "RS256"
EMISSOR = "simpa-auth"
KID = "simpa-auth-1"


@lru_cache
def chave_privada() -> rsa.RSAPrivateKey:
    """Lê a chave privada do volume; na primeira subida, gera e grava uma nova."""
    caminho = Path(get_settings().chaves_dir) / "privada.pem"
    if caminho.exists():
        chave = serialization.load_pem_private_key(caminho.read_bytes(), password=None)
        if not isinstance(chave, rsa.RSAPrivateKey):
            raise TypeError(f"{caminho} não contém uma chave RSA")
        return chave

    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(
        chave.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    caminho.chmod(0o600)
    return chave


def jwks() -> dict[str, list[dict[str, Any]]]:
    """Chave pública no formato JWKS, lido pelos outros serviços."""
    jwk = json.loads(RSAAlgorithm.to_jwk(chave_privada().public_key()))
    jwk.update({"kid": KID, "use": "sig", "alg": ALGORITMO})
    return {"keys": [jwk]}


def criar_token(
    usuario_id: int, role: str, nome: str | None = None, aluno_id: int | None = None
) -> str:
    """Token com o id do usuário (sub), o nome, o perfil (role, D03) e a expiração.

    O perfil aluno leva também `aluno_id`, o cadastro dele no acadêmico.
    """
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "nome": nome,
        "role": role,
        **({"aluno_id": aluno_id} if aluno_id is not None else {}),
        "iss": EMISSOR,
        "iat": agora,
        "exp": agora + timedelta(minutes=get_settings().jwt_expira_minutos),
    }
    return jwt.encode(payload, chave_privada(), algorithm=ALGORITMO, headers={"kid": KID})


# O bcrypt só considera os primeiros 72 bytes; senhas maiores são recusadas no cadastro.
LIMITE_SENHA_BYTES = 72


def gerar_hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def senha_confere(senha: str, senha_hash: str) -> bool:
    senha_bytes = senha.encode()
    if len(senha_bytes) > LIMITE_SENHA_BYTES:
        return False
    return bcrypt.checkpw(senha_bytes, senha_hash.encode())


# ---------- Validação do token nas rotas protegidas do próprio auth ----------

ROLES = {"admin", "coordenador", "professor", "aluno"}
_bearer = HTTPBearer(auto_error=False)


class UsuarioAtual(BaseModel):
    id: int
    role: str
    nome: str | None = None


def usuario_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UsuarioAtual:
    """Valida o token com a própria chave pública; 401 com mensagem genérica (RF09 CA01)."""
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
    if dados.get("role") not in ROLES or not str(dados["sub"]).isdigit():
        raise nao_autenticado

    identificar_usuario(int(dados["sub"]))
    return UsuarioAtual(id=int(dados["sub"]), role=dados["role"], nome=dados.get("nome"))


def exigir_roles(*permitidos: str) -> Callable[[UsuarioAtual], UsuarioAtual]:
    """Dependência que responde 403 se o perfil do token não estiver em `permitidos` (D03)."""
    desconhecidos = set(permitidos) - ROLES
    if desconhecidos:
        raise ValueError(f"Perfis desconhecidos: {sorted(desconhecidos)}")

    def verificar(usuario: Annotated[UsuarioAtual, Depends(usuario_atual)]) -> UsuarioAtual:
        if usuario.role not in permitidos:
            raise AcessoNegado("Seu perfil não tem permissão para esta ação.")
        return usuario

    return verificar
