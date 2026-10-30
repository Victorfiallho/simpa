"""Schemas de entrada e saída do serviço auth."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    senha: Annotated[str, StringConstraints(min_length=1, max_length=72)]


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_usuario: str
    role: str
    ativo: bool
    aluno_id: int | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo do token, não é senha)
    expira_em_minutos: int
    usuario: UsuarioResumo
