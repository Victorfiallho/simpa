"""Dependências comuns das rotas."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Paginacao, paginacao
from app.core.seguranca import UsuarioAtual, usuario_atual

Sessao = Annotated[Session, Depends(get_db)]
Usuario = Annotated[UsuarioAtual, Depends(usuario_atual)]
Pagina = Annotated[Paginacao, Depends(paginacao)]
