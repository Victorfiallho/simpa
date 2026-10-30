"""Registro de acompanhamento do aluno pela coordenação (RF07).

Ao registrar uma ação, os alertas pendentes do aluno passam para "em acompanhamento",
como no protótipo.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clientes import academico
from app.core.excecoes import RecursoNaoEncontrado, RegraDeNegocioViolada
from app.core.seguranca import UsuarioAtual
from app.models import Acompanhamento
from app.schemas.alertas import AcompanhamentoEntrada
from app.services import alertas


def criar(
    db: Session, dados: AcompanhamentoEntrada, usuario: UsuarioAtual, hoje: date | None = None
) -> Acompanhamento:
    hoje = hoje or date.today()
    # Tolerância de um dia, por causa do fuso horário de quem registra.
    if dados.data > hoje + timedelta(days=1):
        raise RegraDeNegocioViolada("A data não pode ser futura.", codigo="DATA_FUTURA")
    if dados.revisao is not None and dados.revisao < dados.data:
        raise RegraDeNegocioViolada(
            "A próxima revisão não pode ser anterior à data da ação.", codigo="REVISAO_ANTERIOR"
        )

    inscricoes = academico.buscar_inscricoes(aluno_id=dados.aluno_id)
    if not inscricoes:
        raise RecursoNaoEncontrado(f"Aluno {dados.aluno_id} não encontrado ou sem inscrições.")
    if dados.disciplina_id is not None and not any(
        i.disciplina.id == dados.disciplina_id for i in inscricoes
    ):
        raise RegraDeNegocioViolada(
            "O aluno não está inscrito nesta disciplina.", codigo="DISCIPLINA_NAO_INSCRITA"
        )

    registro = Acompanhamento(
        aluno_id=dados.aluno_id,
        disciplina_id=dados.disciplina_id,
        tipo=dados.tipo,
        data=dados.data,
        responsavel=dados.responsavel or usuario.nome or f"usuário {usuario.id}",
        responsavel_id=usuario.id,
        observacao=dados.observacao,
        revisao=dados.revisao,
        visivel_ao_aluno=dados.visivel_ao_aluno,
    )
    db.add(registro)
    for alerta in alertas.montar_alertas(db, inscricoes):
        if alerta.estado == "pendente":
            alertas.gravar_estado(db, alerta, "acomp", usuario.id)
    db.commit()
    db.refresh(registro)
    return registro


def listar_do_aluno(db: Session, aluno_id: int) -> list[Acompanhamento]:
    """Mais recentes primeiro."""
    consulta = (
        select(Acompanhamento)
        .where(Acompanhamento.aluno_id == aluno_id)
        .order_by(Acompanhamento.data.desc(), Acompanhamento.id.desc())
    )
    return list(db.scalars(consulta))


def marcar_revisao_feita(db: Session, acompanhamento_id: int) -> Acompanhamento:
    registro = db.get(Acompanhamento, acompanhamento_id)
    if registro is None:
        raise RecursoNaoEncontrado(f"Acompanhamento {acompanhamento_id} não encontrado.")
    if registro.revisao is None:
        raise RegraDeNegocioViolada(
            "Este acompanhamento não tem revisão marcada.", codigo="SEM_REVISAO"
        )
    registro.revisao_feita = True
    db.commit()
    return registro


def revisao_vencida(registro: Acompanhamento, hoje: date | None = None) -> bool:
    return (
        registro.revisao is not None
        and not registro.revisao_feita
        and registro.revisao < (hoje or date.today())
    )
