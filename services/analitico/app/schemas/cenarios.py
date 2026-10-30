"""Schemas de saída dos cenários (RF07). Decimais saem como texto, como no restante (D18)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Categoria = Literal["direta", "recuperacao", "rep_nota", "rep_freq", "sem_dados"]


class RegrasSaida(BaseModel):
    aprovacao: Decimal
    recuperacao: Decimal
    final: Decimal


class ContagemProjetada(BaseModel):
    direta: int
    recuperacao: int
    rep_nota: int
    rep_freq: int
    sem_dados: int


class AlunosProjetados(BaseModel):
    aprovados_em_tudo: int
    com_recuperacao: int
    com_reprovacao: int


class OfertaProjetada(BaseModel):
    oferta: str
    direta: int
    recuperacao: int
    rep_nota: int
    rep_freq: int


class VariacaoDisciplina(BaseModel):
    disciplina_id: int
    disciplina_nome: str
    variacao: Decimal


class MargemSaida(BaseModel):
    inscricao_id: int
    aluno_id: int
    aluno_nome: str
    matricula: str
    disciplina_id: int
    disciplina_nome: str
    modo: Literal["sem_dados", "n2", "aprovado", "exame", "rep_nota"]
    n1: Decimal | None
    n2: Decimal | None
    media: Decimal | None
    frequencia: Decimal | None
    necessario: Decimal | None
    media_maxima: Decimal | None
    viabilidade: str
    gravidade: int
    meta: str
    hipotese_media: Decimal | None = None
    hipotese_resultado: str | None = None


class Projecao(BaseModel):
    regras: RegrasSaida
    base: Literal["n1", "atual"]
    inscricoes_projetadas: int
    contagem: ContagemProjetada
    retencao_percentual: Decimal | None
    alunos: AlunosProjetados
    por_oferta: list[OfertaProjetada]
    variacao_por_disciplina: list[VariacaoDisciplina]
    total_metas: int
    metas: list[MargemSaida]
