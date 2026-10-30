"""Casos de uso de inscrições, avaliações e frequências (RF03, D01, D02, D10, D14).

Depois do commit, cada alteração publica um evento para o analítico recalcular o risco.
"""

from sqlalchemy.orm import Session

from app.core.excecoes import Conflito, RegraDeNegocioViolada
from app.events import publicador
from app.models import Avaliacao, Frequencia, Inscricao, RegistroSemanal
from app.repositories.academico import (
    AlunoRepositorio,
    AvaliacaoRepositorio,
    DisciplinaRepositorio,
    FrequenciaRepositorio,
    InscricaoRepositorio,
    RegistroSemanalRepositorio,
)
from app.schemas.avaliacao import AvaliacaoAtualizacao, AvaliacaoCriacao
from app.schemas.frequencia import FrequenciaAtualizacao, FrequenciaCriacao
from app.schemas.inscricao import InscricaoAtualizacao, InscricaoCriacao
from app.schemas.registro_semanal import RegistroSemanalAtualizacao, RegistroSemanalCriacao
from app.services.comum import (
    garantir_disciplina_aberta,
    garantir_lancamento_permitido,
    mudancas,
    referencia,
)


def _avisar(evento: str, inscricao_id: int) -> None:
    publicador.publicar_sem_falhar(evento, {"inscricao_id": inscricao_id})


# ---------- Inscrições ----------


def criar_inscricao(db: Session, dados: InscricaoCriacao) -> Inscricao:
    repositorio = InscricaoRepositorio(db)
    aluno = referencia(AlunoRepositorio(db), dados.aluno_id)
    disciplina = referencia(DisciplinaRepositorio(db), dados.disciplina_id)
    if aluno.status != "ativo":
        raise RegraDeNegocioViolada(
            f"O aluno {aluno.matricula} está {aluno.status}.", codigo="ALUNO_INATIVO"
        )
    garantir_disciplina_aberta(disciplina)
    if disciplina.status != "ativa":
        raise RegraDeNegocioViolada(
            f"A disciplina {disciplina.nome} está {disciplina.status}.", codigo="DISCIPLINA_INATIVA"
        )
    if repositorio.existe(Inscricao.aluno_id == aluno.id, Inscricao.disciplina_id == disciplina.id):
        raise Conflito("O aluno já está inscrito nesta disciplina.", codigo="INSCRICAO_DUPLICADA")
    inscricao = repositorio.adicionar(Inscricao(aluno_id=aluno.id, disciplina_id=disciplina.id))
    db.commit()
    db.refresh(inscricao)
    _avisar("inscricao.alterada", inscricao.id)
    return inscricao


def atualizar_inscricao(db: Session, inscricao_id: int, dados: InscricaoAtualizacao) -> Inscricao:
    repositorio = InscricaoRepositorio(db)
    inscricao = repositorio.obter_ou_falhar(inscricao_id)
    garantir_disciplina_aberta(inscricao.disciplina)
    repositorio.atualizar(inscricao, mudancas(dados))
    db.commit()
    _avisar("inscricao.alterada", inscricao.id)
    return inscricao


def cancelar_inscricao(db: Session, inscricao_id: int) -> Inscricao:
    """DELETE lógico: a inscrição fica com status cancelada e o histórico é mantido."""
    repositorio = InscricaoRepositorio(db)
    inscricao = repositorio.obter_ou_falhar(inscricao_id)
    garantir_disciplina_aberta(inscricao.disciplina)
    repositorio.atualizar(inscricao, {"status": "cancelada"})
    db.commit()
    _avisar("inscricao.alterada", inscricao.id)
    return inscricao


# ---------- Avaliações ----------


def criar_avaliacao(db: Session, dados: AvaliacaoCriacao) -> Avaliacao:
    inscricao = referencia(InscricaoRepositorio(db), dados.inscricao_id)
    garantir_lancamento_permitido(inscricao)
    avaliacao = AvaliacaoRepositorio(db).adicionar(Avaliacao(**dados.model_dump()))
    db.commit()
    db.refresh(avaliacao)
    _avisar("avaliacao.alterada", inscricao.id)
    return avaliacao


def atualizar_avaliacao(db: Session, avaliacao_id: int, dados: AvaliacaoAtualizacao) -> Avaliacao:
    repositorio = AvaliacaoRepositorio(db)
    avaliacao = repositorio.obter_ou_falhar(avaliacao_id)
    garantir_lancamento_permitido(avaliacao.inscricao)
    repositorio.atualizar(avaliacao, mudancas(dados))
    db.commit()
    db.refresh(avaliacao)
    _avisar("avaliacao.alterada", avaliacao.inscricao_id)
    return avaliacao


def remover_avaliacao(db: Session, avaliacao_id: int) -> None:
    """Uma nota lançada por engano pode ser apagada enquanto a disciplina está aberta."""
    repositorio = AvaliacaoRepositorio(db)
    avaliacao = repositorio.obter_ou_falhar(avaliacao_id)
    garantir_lancamento_permitido(avaliacao.inscricao)
    inscricao_id = avaliacao.inscricao_id
    repositorio.remover(avaliacao)
    db.commit()
    _avisar("avaliacao.alterada", inscricao_id)


# ---------- Frequências ----------


def _periodo_livre(
    repositorio: FrequenciaRepositorio, inscricao_id: int, periodo: str, id_atual: int | None = None
) -> None:
    condicoes = [Frequencia.inscricao_id == inscricao_id, Frequencia.periodo_avaliacao == periodo]
    if id_atual is not None:
        condicoes.append(Frequencia.id != id_atual)
    if repositorio.existe(*condicoes):
        raise Conflito(
            f"Já existe frequência lançada no período {periodo} para esta inscrição.",
            codigo="FREQUENCIA_DUPLICADA",
        )


def criar_frequencia(db: Session, dados: FrequenciaCriacao) -> Frequencia:
    repositorio = FrequenciaRepositorio(db)
    inscricao = referencia(InscricaoRepositorio(db), dados.inscricao_id)
    garantir_lancamento_permitido(inscricao)
    _periodo_livre(repositorio, inscricao.id, dados.periodo_avaliacao)
    frequencia = repositorio.adicionar(Frequencia(**dados.model_dump()))
    db.commit()
    _avisar("frequencia.alterada", inscricao.id)
    return frequencia


def atualizar_frequencia(
    db: Session, frequencia_id: int, dados: FrequenciaAtualizacao
) -> Frequencia:
    repositorio = FrequenciaRepositorio(db)
    frequencia = repositorio.obter_ou_falhar(frequencia_id)
    garantir_lancamento_permitido(frequencia.inscricao)
    alteracoes = mudancas(dados)

    aulas = alteracoes.get("aulas_previstas", frequencia.aulas_previstas)
    faltas = alteracoes.get("faltas", frequencia.faltas)
    if faltas > aulas:
        raise RegraDeNegocioViolada(
            "As faltas não podem passar das aulas previstas.", codigo="FALTAS_INVALIDAS"
        )
    if "periodo_avaliacao" in alteracoes:
        _periodo_livre(
            repositorio, frequencia.inscricao_id, alteracoes["periodo_avaliacao"], frequencia.id
        )

    repositorio.atualizar(frequencia, alteracoes)
    db.commit()
    _avisar("frequencia.alterada", frequencia.inscricao_id)
    return frequencia


def remover_frequencia(db: Session, frequencia_id: int) -> None:
    repositorio = FrequenciaRepositorio(db)
    frequencia = repositorio.obter_ou_falhar(frequencia_id)
    garantir_lancamento_permitido(frequencia.inscricao)
    inscricao_id = frequencia.inscricao_id
    repositorio.remover(frequencia)
    db.commit()
    _avisar("frequencia.alterada", inscricao_id)


# ---------- Registro semanal (presença e atividades) ----------


def _semana_livre(
    repositorio: RegistroSemanalRepositorio,
    inscricao_id: int,
    semana_inicio,
) -> None:
    if repositorio.existe(
        RegistroSemanal.inscricao_id == inscricao_id,
        RegistroSemanal.semana_inicio == semana_inicio,
    ):
        raise Conflito(
            f"Já existe registro da semana de {semana_inicio:%d/%m/%Y} para esta inscrição.",
            codigo="SEMANA_DUPLICADA",
        )


def criar_semana(db: Session, dados: RegistroSemanalCriacao) -> RegistroSemanal:
    repositorio = RegistroSemanalRepositorio(db)
    inscricao = referencia(InscricaoRepositorio(db), dados.inscricao_id)
    garantir_lancamento_permitido(inscricao)
    _semana_livre(repositorio, inscricao.id, dados.semana_inicio)
    registro = repositorio.adicionar(RegistroSemanal(**dados.model_dump()))
    db.commit()
    return registro


def atualizar_semana(
    db: Session, registro_id: int, dados: RegistroSemanalAtualizacao
) -> RegistroSemanal:
    repositorio = RegistroSemanalRepositorio(db)
    registro = repositorio.obter_ou_falhar(registro_id)
    garantir_lancamento_permitido(registro.inscricao)
    alteracoes = mudancas(dados)
    previstas = alteracoes.get("atividades_previstas", registro.atividades_previstas)
    entregues = alteracoes.get("atividades_entregues", registro.atividades_entregues)
    if entregues > previstas:
        raise RegraDeNegocioViolada(
            "As atividades entregues não podem passar das previstas.",
            codigo="ENTREGAS_INVALIDAS",
        )
    repositorio.atualizar(registro, alteracoes)
    db.commit()
    return registro


def remover_semana(db: Session, registro_id: int) -> None:
    repositorio = RegistroSemanalRepositorio(db)
    registro = repositorio.obter_ou_falhar(registro_id)
    garantir_lancamento_permitido(registro.inscricao)
    repositorio.remover(registro)
    db.commit()
