"""Repositório genérico (padrão Repository): o único lugar que monta consultas ao banco.

Regra de transação: o repositório só faz add/flush. Quem chama commit() é o service,
uma vez por caso de uso.
"""

from collections.abc import Iterable
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.excecoes import RecursoNaoEncontrado, RegraDeNegocioViolada
from app.core.paginacao import Paginacao

M = TypeVar("M", bound=Base)


class Repositorio(Generic[M]):
    modelo: type[M]
    nome: ClassVar[str]
    campos_ordenaveis: ClassVar[frozenset[str]] = frozenset({"id"})

    def __init__(self, db: Session):
        self.db = db

    def obter(self, id_: int) -> M | None:
        return self.db.get(self.modelo, id_)

    def obter_ou_falhar(self, id_: int) -> M:
        objeto = self.obter(id_)
        if objeto is None:
            raise RecursoNaoEncontrado(f"{self.nome} {id_} não encontrado(a).")
        return objeto

    def listar(
        self,
        paginacao: Paginacao,
        filtros: dict[str, Any] | None = None,
        condicoes: Iterable[ColumnElement[bool]] = (),
    ) -> tuple[list[M], int]:
        """Lista com filtros de igualdade, condições extras, ordenação e paginação."""
        if paginacao.ordenar_por not in self.campos_ordenaveis:
            permitidos = ", ".join(sorted(self.campos_ordenaveis))
            raise RegraDeNegocioViolada(
                f"Não é possível ordenar por '{paginacao.ordenar_por}'. Use: {permitidos}.",
                codigo="ORDENACAO_INVALIDA",
            )

        consulta = select(self.modelo)
        for campo, valor in (filtros or {}).items():
            if valor is not None:
                consulta = consulta.where(getattr(self.modelo, campo) == valor)
        for condicao in condicoes:
            consulta = consulta.where(condicao)

        total = self.db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        coluna = getattr(self.modelo, paginacao.ordenar_por)
        ordem = coluna.desc() if paginacao.ordem == "desc" else coluna.asc()
        itens = self.db.scalars(
            consulta.order_by(ordem, self.modelo.id)  # type: ignore[attr-defined]
            .offset(paginacao.deslocamento)
            .limit(paginacao.limite)
        ).all()
        return list(itens), total

    def existe(self, *condicoes: ColumnElement[bool]) -> bool:
        consulta = select(self.modelo.id).where(*condicoes).limit(1)  # type: ignore[attr-defined]
        return self.db.scalar(consulta) is not None

    def adicionar(self, objeto: M) -> M:
        self.db.add(objeto)
        self.db.flush()
        return objeto

    def atualizar(self, objeto: M, dados: dict[str, Any]) -> M:
        for campo, valor in dados.items():
            setattr(objeto, campo, valor)
        self.db.flush()
        return objeto

    def remover(self, objeto: M) -> None:
        self.db.delete(objeto)
        self.db.flush()
