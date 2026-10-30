"""Schemas de entrada e saída do serviço auth."""

from datetime import datetime
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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo do token, não é senha)
    expira_em_minutos: int
    usuario: UsuarioResumo


class RegistroAuditoria(BaseModel):
    """Linha da trilha de auditoria (RF12). Sem corpo, token, senha ou CPF (RNF04)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    correlation_id: str
    usuario_id: int | None
    rota: str
    metodo_http: str
    status_http: int
    ip_origem: str
    tempo_resposta_ms: int
    timestamp: datetime
