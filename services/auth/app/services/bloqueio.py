"""Bloqueio temporário do login após tentativas erradas (RF09, RNF04).

Depois de `login_max_tentativas` erros seguidos para o mesmo e-mail, o login fica bloqueado por
`login_bloqueio_segundos`, mesmo que a senha certa seja enviada nesse período. Um login correto
zera a contagem. O bloqueio vale para qualquer e-mail, cadastrado ou não, para não revelar quais
existem.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.excecoes import MuitasTentativas
from app.models import BloqueioLogin


def _chave(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def _com_fuso(momento: datetime) -> datetime:
    """O SQLite devolve datas sem fuso; o Postgres, com."""
    return momento if momento.tzinfo else momento.replace(tzinfo=UTC)


def _registro(db: Session, email: str) -> BloqueioLogin | None:
    return db.scalar(select(BloqueioLogin).where(BloqueioLogin.chave == _chave(email)))


def garantir_liberado(db: Session, email: str, agora: datetime | None = None) -> None:
    """Levanta MuitasTentativas (429) se o e-mail ainda está bloqueado."""
    agora = agora or datetime.now(UTC)
    registro = _registro(db, email)
    if registro is None or registro.bloqueado_ate is None:
        return
    restante = _com_fuso(registro.bloqueado_ate) - agora
    if restante.total_seconds() > 0:
        raise MuitasTentativas(
            f"Muitas tentativas. Tente novamente em {ceil(restante.total_seconds())} segundos.",
            espera_segundos=ceil(restante.total_seconds()),
        )


def registrar_falha(db: Session, email: str, agora: datetime | None = None) -> None:
    """Conta um erro e, ao chegar no limite, inicia o bloqueio. Quem chama confirma a transação."""
    agora = agora or datetime.now(UTC)
    configuracao = get_settings()
    registro = _registro(db, email)
    if registro is None:
        registro = BloqueioLogin(chave=_chave(email), falhas=0)
        db.add(registro)
    elif registro.bloqueado_ate is not None and _com_fuso(registro.bloqueado_ate) <= agora:
        # O bloqueio anterior já acabou: recomeça a contagem.
        registro.falhas = 0
        registro.bloqueado_ate = None
    registro.falhas += 1
    if registro.falhas >= configuracao.login_max_tentativas:
        registro.bloqueado_ate = agora + timedelta(seconds=configuracao.login_bloqueio_segundos)
        registro.falhas = 0


def limpar(db: Session, email: str) -> None:
    """Login correto: zera a contagem. Quem chama confirma a transação."""
    registro = _registro(db, email)
    if registro is not None:
        db.delete(registro)
