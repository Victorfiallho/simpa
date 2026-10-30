"""Rotas de inscrições, avaliações e frequências (RF03, RF08)."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencias import EXIGE_GESTOR, Lancador, Pagina, Sessao, Usuario
from app.core.respostas import Resposta, RespostaPaginada, resposta, resposta_paginada
from app.models import Avaliacao, Frequencia, RegistroSemanal
from app.repositories.academico import (
    AvaliacaoRepositorio,
    FrequenciaRepositorio,
    InscricaoRepositorio,
    RegistroSemanalRepositorio,
)
from app.schemas.avaliacao import AvaliacaoAtualizacao, AvaliacaoCriacao, AvaliacaoLeitura
from app.schemas.frequencia import FrequenciaAtualizacao, FrequenciaCriacao, FrequenciaLeitura
from app.schemas.inscricao import (
    InscricaoAtualizacao,
    InscricaoCriacao,
    InscricaoLeitura,
    StatusInscricao,
)
from app.schemas.registro_semanal import (
    RegistroSemanalAtualizacao,
    RegistroSemanalCriacao,
    RegistroSemanalLeitura,
)
from app.services import escopo, lancamentos

inscricoes = APIRouter(prefix="/inscricoes", tags=["Inscrições"])
avaliacoes = APIRouter(prefix="/avaliacoes", tags=["Avaliações"])
frequencias = APIRouter(prefix="/frequencias", tags=["Frequências"])
semanas = APIRouter(prefix="/semanas", tags=["Registro semanal"])

# ---------- Inscrições ----------


@inscricoes.get("", response_model=RespostaPaginada[InscricaoLeitura])
def listar_inscricoes(
    db: Sessao,
    pagina: Pagina,
    usuario: Usuario,
    aluno_id: int | None = None,
    disciplina_id: int | None = None,
    status_: Annotated[StatusInscricao | None, Query(alias="status")] = None,
):
    itens, total = InscricaoRepositorio(db).listar(
        pagina,
        {"aluno_id": aluno_id, "disciplina_id": disciplina_id, "status": status_},
        escopo.condicao_inscricoes(usuario),
    )
    return resposta_paginada(InscricaoLeitura, itens, total, pagina.pagina, pagina.limite)


@inscricoes.get("/{inscricao_id}", response_model=Resposta[InscricaoLeitura])
def obter_inscricao(inscricao_id: int, db: Sessao, usuario: Usuario):
    inscricao = InscricaoRepositorio(db).obter_ou_falhar(inscricao_id)
    escopo.garantir_inscricao_propria(inscricao, usuario)
    return resposta(InscricaoLeitura, inscricao)


@inscricoes.post(
    "",
    response_model=Resposta[InscricaoLeitura],
    status_code=status.HTTP_201_CREATED,
    dependencies=[EXIGE_GESTOR],
)
def criar_inscricao(dados: InscricaoCriacao, db: Sessao):
    inscricao = lancamentos.criar_inscricao(db, dados)
    return resposta(InscricaoLeitura, inscricao, "Inscrição realizada.")


@inscricoes.patch(
    "/{inscricao_id}", response_model=Resposta[InscricaoLeitura], dependencies=[EXIGE_GESTOR]
)
def atualizar_inscricao(inscricao_id: int, dados: InscricaoAtualizacao, db: Sessao):
    inscricao = lancamentos.atualizar_inscricao(db, inscricao_id, dados)
    return resposta(InscricaoLeitura, inscricao, "Inscrição atualizada.")


@inscricoes.delete(
    "/{inscricao_id}", response_model=Resposta[InscricaoLeitura], dependencies=[EXIGE_GESTOR]
)
def cancelar_inscricao(inscricao_id: int, db: Sessao):
    inscricao = lancamentos.cancelar_inscricao(db, inscricao_id)
    return resposta(InscricaoLeitura, inscricao, "Inscrição cancelada.")


# ---------- Avaliações ----------


@avaliacoes.get("", response_model=RespostaPaginada[AvaliacaoLeitura])
def listar_avaliacoes(
    db: Sessao,
    pagina: Pagina,
    usuario: Usuario,
    inscricao_id: int | None = None,
    periodo_avaliacao: str | None = None,
):
    itens, total = AvaliacaoRepositorio(db).listar(
        pagina,
        {"inscricao_id": inscricao_id, "periodo_avaliacao": periodo_avaliacao},
        escopo.condicao_por_inscricao(usuario, Avaliacao.inscricao_id),
    )
    return resposta_paginada(AvaliacaoLeitura, itens, total, pagina.pagina, pagina.limite)


@avaliacoes.get("/{avaliacao_id}", response_model=Resposta[AvaliacaoLeitura])
def obter_avaliacao(avaliacao_id: int, db: Sessao, usuario: Usuario):
    avaliacao = AvaliacaoRepositorio(db).obter_ou_falhar(avaliacao_id)
    escopo.garantir_inscricao_propria(avaliacao.inscricao, usuario)
    return resposta(AvaliacaoLeitura, avaliacao)


@avaliacoes.post("", response_model=Resposta[AvaliacaoLeitura], status_code=status.HTTP_201_CREATED)
def lancar_avaliacao(dados: AvaliacaoCriacao, db: Sessao, usuario: Lancador):
    avaliacao = lancamentos.criar_avaliacao(db, dados, usuario)
    return resposta(AvaliacaoLeitura, avaliacao, "Nota lançada.")


@avaliacoes.patch("/{avaliacao_id}", response_model=Resposta[AvaliacaoLeitura])
def atualizar_avaliacao(
    avaliacao_id: int, dados: AvaliacaoAtualizacao, db: Sessao, usuario: Lancador
):
    avaliacao = lancamentos.atualizar_avaliacao(db, avaliacao_id, dados, usuario)
    return resposta(AvaliacaoLeitura, avaliacao, "Nota atualizada.")


@avaliacoes.delete("/{avaliacao_id}", response_model=Resposta[None])
def remover_avaliacao(avaliacao_id: int, db: Sessao, usuario: Lancador):
    lancamentos.remover_avaliacao(db, avaliacao_id, usuario)
    return Resposta[None](mensagem="Nota removida.")


# ---------- Frequências ----------


@frequencias.get("", response_model=RespostaPaginada[FrequenciaLeitura])
def listar_frequencias(
    db: Sessao,
    pagina: Pagina,
    usuario: Usuario,
    inscricao_id: int | None = None,
    periodo_avaliacao: str | None = None,
):
    itens, total = FrequenciaRepositorio(db).listar(
        pagina,
        {"inscricao_id": inscricao_id, "periodo_avaliacao": periodo_avaliacao},
        escopo.condicao_por_inscricao(usuario, Frequencia.inscricao_id),
    )
    return resposta_paginada(FrequenciaLeitura, itens, total, pagina.pagina, pagina.limite)


@frequencias.get("/{frequencia_id}", response_model=Resposta[FrequenciaLeitura])
def obter_frequencia(frequencia_id: int, db: Sessao, usuario: Usuario):
    frequencia = FrequenciaRepositorio(db).obter_ou_falhar(frequencia_id)
    escopo.garantir_inscricao_propria(frequencia.inscricao, usuario)
    return resposta(FrequenciaLeitura, frequencia)


@frequencias.post(
    "", response_model=Resposta[FrequenciaLeitura], status_code=status.HTTP_201_CREATED
)
def lancar_frequencia(dados: FrequenciaCriacao, db: Sessao, usuario: Lancador):
    frequencia = lancamentos.criar_frequencia(db, dados, usuario)
    return resposta(FrequenciaLeitura, frequencia, "Frequência lançada.")


@frequencias.patch("/{frequencia_id}", response_model=Resposta[FrequenciaLeitura])
def atualizar_frequencia(
    frequencia_id: int, dados: FrequenciaAtualizacao, db: Sessao, usuario: Lancador
):
    frequencia = lancamentos.atualizar_frequencia(db, frequencia_id, dados, usuario)
    return resposta(FrequenciaLeitura, frequencia, "Frequência atualizada.")


@frequencias.delete("/{frequencia_id}", response_model=Resposta[None])
def remover_frequencia(frequencia_id: int, db: Sessao, usuario: Lancador):
    lancamentos.remover_frequencia(db, frequencia_id, usuario)
    return Resposta[None](mensagem="Frequência removida.")


# ---------- Registro semanal (presença e atividades) ----------


@semanas.get("", response_model=RespostaPaginada[RegistroSemanalLeitura])
def listar_semanas(db: Sessao, pagina: Pagina, usuario: Usuario, inscricao_id: int | None = None):
    itens, total = RegistroSemanalRepositorio(db).listar(
        pagina,
        {"inscricao_id": inscricao_id},
        escopo.condicao_por_inscricao(usuario, RegistroSemanal.inscricao_id),
    )
    return resposta_paginada(RegistroSemanalLeitura, itens, total, pagina.pagina, pagina.limite)


@semanas.get("/{registro_id}", response_model=Resposta[RegistroSemanalLeitura])
def obter_semana(registro_id: int, db: Sessao, usuario: Usuario):
    registro = RegistroSemanalRepositorio(db).obter_ou_falhar(registro_id)
    escopo.garantir_inscricao_propria(registro.inscricao, usuario)
    return resposta(RegistroSemanalLeitura, registro)


@semanas.post(
    "", response_model=Resposta[RegistroSemanalLeitura], status_code=status.HTTP_201_CREATED
)
def lancar_semana(dados: RegistroSemanalCriacao, db: Sessao, usuario: Lancador):
    registro = lancamentos.criar_semana(db, dados, usuario)
    return resposta(RegistroSemanalLeitura, registro, "Semana registrada.")


@semanas.patch("/{registro_id}", response_model=Resposta[RegistroSemanalLeitura])
def atualizar_semana(
    registro_id: int, dados: RegistroSemanalAtualizacao, db: Sessao, usuario: Lancador
):
    registro = lancamentos.atualizar_semana(db, registro_id, dados, usuario)
    return resposta(RegistroSemanalLeitura, registro, "Semana atualizada.")


@semanas.delete("/{registro_id}", response_model=Resposta[None])
def remover_semana(registro_id: int, db: Sessao, usuario: Lancador):
    lancamentos.remover_semana(db, registro_id, usuario)
    return Resposta[None](mensagem="Registro semanal removido.")
