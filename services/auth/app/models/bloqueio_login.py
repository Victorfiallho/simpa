from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BloqueioLogin(Base):
    """Tentativas de login erradas por e-mail, para o bloqueio temporário (RF09, RNF04).

    A chave é o hash do e-mail, assim o bloqueio vale igual para e-mails que existem e que não
    existem (a resposta não revela quais estão cadastrados) e a tabela não guarda o e-mail.
    """

    __tablename__ = "bloqueio_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(64), unique=True)
    falhas: Mapped[int] = mapped_column(default=0, server_default="0")
    bloqueado_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
