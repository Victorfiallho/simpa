"""Schemas do copiloto: pergunta em linguagem natural e resposta estruturada (RF07)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Intencao = Literal[
    "resumo",
    "aluno",
    "filtro",
    "monitoria",
    "contagem",
    "situacao",
    "alertas",
    "projecao",
    "fora_do_escopo",
    "desconhecido",
    "ajuda",
]


class Pergunta(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pergunta: Annotated[str, StringConstraints(min_length=2, max_length=300)]


class ItemResposta(BaseModel):
    aluno_id: int
    aluno_nome: str
    matricula: str
    detalhe: str


class SecaoResumo(BaseModel):
    titulo: str
    linhas: list[str]


class RespostaCopiloto(BaseModel):
    """O texto já vem pronto para exibir. Os itens são alunos que o front pode tornar clicáveis."""

    intencao: Intencao
    recorte: str
    texto: str
    itens: list[ItemResposta] = []
    total_itens: int = 0
    secoes: list[SecaoResumo] = []
    texto_completo: str | None = None
    sugestoes: list[str] = []
