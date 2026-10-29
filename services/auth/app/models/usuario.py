from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ROLES = ("admin", "coordenador", "professor")


class Usuario(Base):
    """Usuário do sistema com um dos três perfis da D03."""

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(f"role IN ({', '.join(repr(r) for r in ROLES)})", name="role_valida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_usuario: Mapped[str] = mapped_column(String(60), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # Hash bcrypt; a senha em texto puro nunca é gravada (Restrição 1).
    senha_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(12))
    ativo: Mapped[bool] = mapped_column(default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
