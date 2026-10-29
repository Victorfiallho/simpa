"""Casos de uso de usuários e login (RF09, D03)."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.excecoes import Conflito
from app.core.seguranca import criar_token, gerar_hash_senha, senha_confere
from app.models import Usuario
from app.schemas import Token, UsuarioResumo

logger = logging.getLogger("auth.usuarios")

# Hash de uma senha qualquer: comparar contra ele quando o e-mail não existe deixa o tempo
# de resposta igual ao de uma senha errada, sem revelar quais e-mails estão cadastrados.
_HASH_FALSO = gerar_hash_senha("senha-que-nunca-confere")


def autenticar(db: Session, email: str, senha: str) -> Token | None:
    """Devolve o token, ou None sem dizer se o erro foi no e-mail ou na senha (RF09 CA01)."""
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email.lower()))
    if usuario is None:
        senha_confere(senha, _HASH_FALSO)
        return None
    if not senha_confere(senha, usuario.senha_hash) or not usuario.ativo:
        return None
    return Token(
        access_token=criar_token(usuario.id, usuario.role),
        expira_em_minutos=get_settings().jwt_expira_minutos,
        usuario=UsuarioResumo.model_validate(usuario),
    )


def criar_usuario(db: Session, nome_usuario: str, email: str, senha: str, role: str) -> Usuario:
    existe = db.scalar(
        select(Usuario.id).where(
            (Usuario.nome_usuario == nome_usuario) | (func.lower(Usuario.email) == email.lower())
        )
    )
    if existe is not None:
        raise Conflito("Nome de usuário ou e-mail já cadastrado.", codigo="USUARIO_DUPLICADO")
    usuario = Usuario(
        nome_usuario=nome_usuario,
        email=email.lower(),
        senha_hash=gerar_hash_senha(senha),
        role=role,
    )
    db.add(usuario)
    db.commit()
    return usuario


USUARIOS_DEMO = [
    ("admin", "admin@simpa.dev", "admin"),
    ("coordenacao", "coordenacao@simpa.dev", "coordenador"),
    ("prof.ana", "ana.prof@simpa.dev", "professor"),
    ("prof.bruno", "bruno.prof@simpa.dev", "professor"),
    ("prof.carla", "carla.prof@simpa.dev", "professor"),
]


def garantir_usuarios_demo(db: Session, senha: str) -> None:
    """Cria um usuário de cada perfil para a demonstração, se ainda não existirem."""
    for nome_usuario, email, role in USUARIOS_DEMO:
        if db.scalar(select(Usuario.id).where(Usuario.nome_usuario == nome_usuario)) is None:
            criar_usuario(db, nome_usuario, email, senha, role)
            logger.info(
                "usuario de demonstracao criado", extra={"dados": {"usuario": nome_usuario}}
            )
