from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

ROLES = ("admin", "coordenador", "professor", "aluno")


class Usuario(Base):
    """Usuário do sistema: os três perfis da D03 e o aluno (consulta do próprio desempenho)."""

    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint(f"role IN ({', '.join(repr(r) for r in ROLES)})", name="role_valida"),
        # O aluno precisa apontar para o seu cadastro no acadêmico; os demais perfis não.
        CheckConstraint("(role = 'aluno') = (aluno_id IS NOT NULL)", name="aluno_com_cadastro"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_usuario: Mapped[str] = mapped_column(String(60), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # Hash bcrypt; a senha em texto puro nunca é gravada (Restrição 1).
    senha_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(12))
    # Id do Aluno no serviço acadêmico (sem FK: outro banco, D13). Só para o perfil aluno.
    aluno_id: Mapped[int | None] = mapped_column(unique=True)
    ativo: Mapped[bool] = mapped_column(default=True, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
