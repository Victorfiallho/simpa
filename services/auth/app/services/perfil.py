"""Perfil do usuário: dados pessoais e foto (RF09)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.excecoes import RecursoNaoEncontrado, RegraDeNegocioViolada
from app.models import PerfilUsuario, Usuario
from app.schemas_perfil import PerfilAtualizacao, PerfilSaida

TAMANHO_MAXIMO_FOTO = 1024 * 1024  # 1 MB; o front recorta e reduz antes de enviar
# Campos que contam para o "perfil X% completo" (os mesmos do protótipo).
CAMPOS_DO_PERCENTUAL = (
    "nascimento",
    "cpf",
    "telefone",
    "email_contato",
    "cep",
    "rua",
    "numero",
    "bairro",
    "cidade",
    "uf",
    "emergencia_nome",
    "emergencia_telefone",
    "emergencia_parentesco",
)


def tipo_da_imagem(conteudo: bytes) -> str | None:
    """Confere pelos primeiros bytes: o Content-Type enviado pelo cliente não é confiável."""
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    return None


def _usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    return usuario


def obter(db: Session, usuario_id: int) -> PerfilUsuario | None:
    return db.scalar(select(PerfilUsuario).where(PerfilUsuario.usuario_id == usuario_id))


def _ou_criar(db: Session, usuario_id: int) -> PerfilUsuario:
    perfil = obter(db, usuario_id)
    if perfil is None:
        perfil = PerfilUsuario(usuario_id=usuario_id)
        db.add(perfil)
    return perfil


def saida(db: Session, usuario_id: int) -> PerfilSaida:
    usuario = _usuario(db, usuario_id)
    perfil = obter(db, usuario_id)
    campos = {}
    if perfil is not None:
        campos = {c: getattr(perfil, c) for c in PerfilSaida.model_fields if hasattr(perfil, c)}
        campos.pop("usuario_id", None)
    preenchidos = sum(1 for c in CAMPOS_DO_PERCENTUAL if campos.get(c) not in (None, ""))
    return PerfilSaida(
        usuario_id=usuario.id,
        nome_usuario=usuario.nome_usuario,
        role=usuario.role,
        aluno_id=getattr(usuario, "aluno_id", None),  # existe quando o perfil aluno estiver no ar
        **{
            k: v
            for k, v in campos.items()
            if k not in ("nome_usuario", "role", "aluno_id", "tem_foto")
        },
        tem_foto=bool(perfil and perfil.foto),
        preenchimento_percentual=round(preenchidos * 100 / len(CAMPOS_DO_PERCENTUAL)),
    )


def atualizar(db: Session, usuario_id: int, dados: PerfilAtualizacao) -> PerfilSaida:
    _usuario(db, usuario_id)
    alteracoes = dados.model_dump(exclude_unset=True)
    perfil = _ou_criar(db, usuario_id)
    for campo, valor in alteracoes.items():
        setattr(perfil, campo, valor)
    db.commit()
    return saida(db, usuario_id)


def salvar_foto(db: Session, usuario_id: int, conteudo: bytes) -> None:
    _usuario(db, usuario_id)
    if not conteudo:
        raise RegraDeNegocioViolada("Envie a imagem no corpo da requisição.", codigo="FOTO_VAZIA")
    if len(conteudo) > TAMANHO_MAXIMO_FOTO:
        raise RegraDeNegocioViolada(
            "A foto passa de 1 MB. Reduza a imagem antes de enviar.", codigo="FOTO_GRANDE"
        )
    tipo = tipo_da_imagem(conteudo)
    if tipo is None:
        raise RegraDeNegocioViolada(
            "Formato não aceito. Envie uma imagem JPG, PNG ou WebP.", codigo="FOTO_INVALIDA"
        )
    perfil = _ou_criar(db, usuario_id)
    perfil.foto, perfil.foto_tipo = conteudo, tipo
    db.commit()


def remover_foto(db: Session, usuario_id: int) -> None:
    perfil = obter(db, usuario_id)
    if perfil is not None and perfil.foto is not None:
        perfil.foto, perfil.foto_tipo = None, None
        db.commit()


def foto_de(db: Session, usuario_id: int) -> tuple[bytes, str]:
    perfil = obter(db, usuario_id)
    if perfil is None or perfil.foto is None or perfil.foto_tipo is None:
        raise RecursoNaoEncontrado("Este usuário não tem foto.")
    return perfil.foto, perfil.foto_tipo
