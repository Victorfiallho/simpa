"""Rotas de inscrições, avaliações e frequências (RF03, RF08)."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencias import Pagina, Sessao
from app.core.respostas import Resposta, RespostaPaginada, resposta, resposta_paginada
from app.repositories.academico import (
    AvaliacaoRepositorio,
    FrequenciaRepositorio,
    InscricaoRepositorio,
)
from app.schemas.avaliacao import AvaliacaoAtualizacao, AvaliacaoCriacao, AvaliacaoLeitura
from app.schemas.frequencia import FrequenciaAtualizacao, FrequenciaCriacao, FrequenciaLeitura
from app.schemas.inscricao import (
    InscricaoAtualizacao,
    InscricaoCriacao,
    InscricaoLeitura,
    StatusInscricao,
)
from app.services import lancamentos

inscricoes = APIRouter(prefix="/inscricoes", tags=["Inscrições"])
avaliacoes = APIRouter(prefix="/avaliacoes", tags=["Avaliações"])
frequencias = APIRouter(prefix="/frequencias", tags=["Frequências"])

# ---------- Inscrições ----------


@inscricoes.get("", response_model=RespostaPaginada[InscricaoLeitura])
def listar_inscricoes(
    db: Sessao,
    pagina: Pagina,
    aluno_id: int | None = None,
    disciplina_id: int | None = None,
    status_: Annotated[StatusInscricao | None, Query(alias="status")] = None,
):
    itens, total = InscricaoRepositorio(db).listar(
        pagina, {"aluno_id": aluno_id, "disciplina_id": disciplina_id, "status": status_}
    )
    return resposta_paginada(InscricaoLeitura, itens, total, pagina.pagina, pagina.limite)


@inscricoes.get("/{inscricao_id}", response_model=Resposta[InscricaoLeitura])
def obter_inscricao(inscricao_id: int, db: Sessao):
    return resposta(InscricaoLeitura, InscricaoRepositorio(db).obter_ou_falhar(inscricao_id))


@inscricoes.post("", response_model=Resposta[InscricaoLeitura], status_code=status.HTTP_201_CREATED)
def criar_inscricao(dados: InscricaoCriacao, db: Sessao):
    inscricao = lancamentos.criar_inscricao(db, dados)
    return resposta(InscricaoLeitura, inscricao, "Inscrição realizada.")


@inscricoes.patch("/{inscricao_id}", response_model=Resposta[InscricaoLeitura])
def atualizar_inscricao(inscricao_id: int, dados: InscricaoAtualizacao, db: Sessao):
    inscricao = lancamentos.atualizar_inscricao(db, inscricao_id, dados)
    return resposta(InscricaoLeitura, inscricao, "Inscrição atualizada.")


@inscricoes.delete("/{inscricao_id}", response_model=Resposta[InscricaoLeitura])
def cancelar_inscricao(inscricao_id: int, db: Sessao):
    inscricao = lancamentos.cancelar_inscricao(db, inscricao_id)
    return resposta(InscricaoLeitura, inscricao, "Inscrição cancelada.")


# ---------- Avaliações ----------


@avaliacoes.get("", response_model=RespostaPaginada[AvaliacaoLeitura])
def listar_avaliacoes(
    db: Sessao,
    pagina: Pagina,
    inscricao_id: int | None = None,
    periodo_avaliacao: str | None = None,
):
    itens, total = AvaliacaoRepositorio(db).listar(
        pagina, {"inscricao_id": inscricao_id, "periodo_avaliacao": periodo_avaliacao}
    )
    return resposta_paginada(AvaliacaoLeitura, itens, total, pagina.pagina, pagina.limite)


@avaliacoes.get("/{avaliacao_id}", response_model=Resposta[AvaliacaoLeitura])
def obter_avaliacao(avaliacao_id: int, db: Sessao):
    return resposta(AvaliacaoLeitura, AvaliacaoRepositorio(db).obter_ou_falhar(avaliacao_id))


@avaliacoes.post("", response_model=Resposta[AvaliacaoLeitura], status_code=status.HTTP_201_CREATED)
def lancar_avaliacao(dados: AvaliacaoCriacao, db: Sessao):
    avaliacao = lancamentos.criar_avaliacao(db, dados)
    return resposta(AvaliacaoLeitura, avaliacao, "Nota lançada.")


@avaliacoes.patch("/{avaliacao_id}", response_model=Resposta[AvaliacaoLeitura])
def atualizar_avaliacao(avaliacao_id: int, dados: AvaliacaoAtualizacao, db: Sessao):
    avaliacao = lancamentos.atualizar_avaliacao(db, avaliacao_id, dados)
    return resposta(AvaliacaoLeitura, avaliacao, "Nota atualizada.")


@avaliacoes.delete("/{avaliacao_id}", response_model=Resposta[None])
def remover_avaliacao(avaliacao_id: int, db: Sessao):
    lancamentos.remover_avaliacao(db, avaliacao_id)
    return Resposta[None](mensagem="Nota removida.")


# ---------- Frequências ----------


@frequencias.get("", response_model=RespostaPaginada[FrequenciaLeitura])
def listar_frequencias(
    db: Sessao,
    pagina: Pagina,
    inscricao_id: int | None = None,
    periodo_avaliacao: str | None = None,
):
    itens, total = FrequenciaRepositorio(db).listar(
        pagina, {"inscricao_id": inscricao_id, "periodo_avaliacao": periodo_avaliacao}
    )
    return resposta_paginada(FrequenciaLeitura, itens, total, pagina.pagina, pagina.limite)


@frequencias.get("/{frequencia_id}", response_model=Resposta[FrequenciaLeitura])
def obter_frequencia(frequencia_id: int, db: Sessao):
    return resposta(FrequenciaLeitura, FrequenciaRepositorio(db).obter_ou_falhar(frequencia_id))


@frequencias.post(
    "", response_model=Resposta[FrequenciaLeitura], status_code=status.HTTP_201_CREATED
)
def lancar_frequencia(dados: FrequenciaCriacao, db: Sessao):
    frequencia = lancamentos.criar_frequencia(db, dados)
    return resposta(FrequenciaLeitura, frequencia, "Frequência lançada.")


@frequencias.patch("/{frequencia_id}", response_model=Resposta[FrequenciaLeitura])
def atualizar_frequencia(frequencia_id: int, dados: FrequenciaAtualizacao, db: Sessao):
    frequencia = lancamentos.atualizar_frequencia(db, frequencia_id, dados)
    return resposta(FrequenciaLeitura, frequencia, "Frequência atualizada.")


@frequencias.delete("/{frequencia_id}", response_model=Resposta[None])
def remover_frequencia(frequencia_id: int, db: Sessao):
    lancamentos.remover_frequencia(db, frequencia_id)
    return Resposta[None](mensagem="Frequência removida.")
