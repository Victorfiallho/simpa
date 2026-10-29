"""Emissão de tokens JWT (RF09, D15).

O auth é o único serviço com a chave privada. Os outros validam os tokens com a chave
pública, publicada em /.well-known/jwks.json. Assim, nenhum outro serviço consegue
emitir um token, mesmo que seja comprometido.
"""

import json
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import bcrypt
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.core.config import get_settings

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


def criar_token(usuario_id: int, role: str, nome: str | None = None) -> str:
    """Token com o id do usuário (sub), o nome, o perfil (role, D03) e a expiração."""
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "nome": nome,
        "role": role,
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
