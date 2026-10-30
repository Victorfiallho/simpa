from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerfilUsuario(Base):
    """Dados pessoais que o próprio usuário preenche, e a foto dele (1 para 1 com Usuario).

    Tudo é opcional. O CPF é guardado só com os 11 dígitos e as respostas da API o mostram
    mascarado (RNF04). Nome, matrícula e turma do aluno vêm do cadastro, não daqui.
    """

    __tablename__ = "perfil_usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="RESTRICT"), unique=True
    )
    nome_completo: Mapped[str | None] = mapped_column(String(80))
    cargo: Mapped[str | None] = mapped_column(String(60))
    matricula_funcional: Mapped[str | None] = mapped_column(String(20))
    nascimento: Mapped[date | None] = mapped_column(Date)
    cpf: Mapped[str | None] = mapped_column(String(11))
    telefone: Mapped[str | None] = mapped_column(String(11))
    email_contato: Mapped[str | None] = mapped_column(String(254))
    cep: Mapped[str | None] = mapped_column(String(8))
    rua: Mapped[str | None] = mapped_column(String(100))
    numero: Mapped[str | None] = mapped_column(String(10))
    complemento: Mapped[str | None] = mapped_column(String(60))
    bairro: Mapped[str | None] = mapped_column(String(60))
    cidade: Mapped[str | None] = mapped_column(String(60))
    uf: Mapped[str | None] = mapped_column(String(2))
    emergencia_nome: Mapped[str | None] = mapped_column(String(80))
    emergencia_parentesco: Mapped[str | None] = mapped_column(String(40))
    emergencia_telefone: Mapped[str | None] = mapped_column(String(11))
    foto: Mapped[bytes | None] = mapped_column(LargeBinary)
    foto_tipo: Mapped[str | None] = mapped_column(String(15))
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
