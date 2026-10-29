"""Regras compartilhadas pelos services do acadêmico."""

from typing import Any

from pydantic import BaseModel

from app.core.excecoes import AcessoNegado, Conflito, RegraDeNegocioViolada
from app.core.seguranca import UsuarioAtual
from app.models import Disciplina, Inscricao
from app.repositories.base import M, Repositorio


def mudancas(schema: BaseModel, aceitam_nulo: set[str] = frozenset()) -> dict[str, Any]:
    """Campos enviados no PATCH. Nulo só é aceito nos campos opcionais do cadastro."""
    dados = schema.model_dump(exclude_unset=True)
    nulos = sorted(c for c, v in dados.items() if v is None and c not in aceitam_nulo)
    if nulos:
        raise RegraDeNegocioViolada(
            f"Estes campos não podem ficar vazios: {', '.join(nulos)}.", codigo="CAMPO_OBRIGATORIO"
        )
    return dados


def referencia(repositorio: Repositorio[M], id_: int) -> M:
    """Busca uma entidade citada no corpo da requisição; se não existir, é erro do corpo (422)."""
    objeto = repositorio.obter(id_)
    if objeto is None:
        raise RegraDeNegocioViolada(
            f"{repositorio.nome} {id_} não existe.", codigo="REFERENCIA_INVALIDA"
        )
    return objeto


def garantir_reabertura(status_atual: str, status_novo: str | None, usuario: UsuarioAtual) -> None:
    """Só o administrador tira uma turma ou disciplina do status encerrada (D10)."""
    if status_atual == "encerrada" and status_novo not in (None, "encerrada"):
        if usuario.role != "admin":
            raise AcessoNegado(
                "Só o administrador pode reabrir o que está encerrado.",
                codigo="REABERTURA_RESTRITA",
            )


def garantir_disciplina_aberta(disciplina: Disciplina) -> None:
    """Disciplina ou turma encerrada bloqueia inscrições, notas e frequências (D10)."""
    if disciplina.encerrada:
        raise Conflito(
            f"A disciplina {disciplina.nome} está encerrada; os lançamentos estão bloqueados.",
            codigo="DISCIPLINA_ENCERRADA",
        )


def garantir_lancamento_permitido(inscricao: Inscricao) -> None:
    garantir_disciplina_aberta(inscricao.disciplina)
    if inscricao.status != "ativa":
        raise RegraDeNegocioViolada(
            f"A inscrição {inscricao.id} está {inscricao.status}; só inscrições ativas recebem "
            "notas e frequência.",
            codigo="INSCRICAO_INATIVA",
        )
