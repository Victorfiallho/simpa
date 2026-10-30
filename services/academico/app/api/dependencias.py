"""Dependências comuns das rotas."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Paginacao, paginacao
from app.core.seguranca import UsuarioAtual, exigir_roles, usuario_atual

Sessao = Annotated[Session, Depends(get_db)]
Usuario = Annotated[UsuarioAtual, Depends(usuario_atual)]
Pagina = Annotated[Paginacao, Depends(paginacao)]

# D03: cadastros e inscrições: admin e coordenador; notas e frequência: admin e professor.
Gestor = Annotated[UsuarioAtual, Depends(exigir_roles("admin", "coordenador"))]
Lancador = Annotated[UsuarioAtual, Depends(exigir_roles("admin", "professor"))]
EXIGE_GESTOR = Depends(exigir_roles("admin", "coordenador"))
