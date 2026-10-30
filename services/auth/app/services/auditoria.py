"""Grava no banco os registros de auditoria enviados pelos serviços (RF12, RNF16)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import LogRequisicao


class RegistroRequisicao(BaseModel):
    """Só estes campos são aceitos; qualquer outro vindo na mensagem é descartado."""

    model_config = ConfigDict(extra="ignore")

    correlation_id: str = Field(min_length=1, max_length=64)
    usuario_id: int | None = None
    rota: str = Field(max_length=300)
    metodo_http: str = Field(max_length=10)
    status_http: int = Field(ge=100, le=599)
    ip_origem: str = Field(max_length=45)
    tempo_resposta_ms: int = Field(ge=0)
    timestamp: datetime


def gravar_registro(db: Session, dados: dict) -> bool:
    """Grava um registro. Devolve False se o correlation_id já estava gravado.

    O RabbitMQ pode entregar a mesma mensagem mais de uma vez; o `correlation_id` único
    torna a gravação idempotente.
    """
    registro = RegistroRequisicao.model_validate(dados)
    db.add(LogRequisicao(**registro.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True
