from datetime import date
from typing import Annotated, Literal

from pydantic import EmailStr, StringConstraints, field_serializer, field_validator

from app.schemas.base import CPF, Entrada, Saida, Texto, mascarar_cpf
from app.schemas.inscricao import InscricaoDetalhada

StatusAluno = Literal["ativo", "inativo", "transferido", "concluido", "evadido"]
Matricula = Annotated[str, StringConstraints(pattern=r"^\d{4,20}$")]
Telefone = Annotated[str, StringConstraints(min_length=8, max_length=20)]
NomeCompleto = Annotated[str, StringConstraints(min_length=3, max_length=150)]


def _nao_futura(valor: date | None) -> date | None:
    if valor is not None and valor > date.today():
        raise ValueError("A data de nascimento não pode estar no futuro.")
    return valor


class AlunoCriacao(Entrada):
    matricula: Matricula
    nome_completo: NomeCompleto
    cpf: CPF | None = None
    email: EmailStr
    telefone: Telefone | None = None
    data_nascimento: date | None = None
    curso: Texto
    turma_id: int

    @field_validator("data_nascimento")
    @classmethod
    def validar_data_nascimento(cls, valor: date | None) -> date | None:
        return _nao_futura(valor)


class AlunoAtualizacao(Entrada):
    nome_completo: NomeCompleto | None = None
    cpf: CPF | None = None
    email: EmailStr | None = None
    telefone: Telefone | None = None
    data_nascimento: date | None = None
    curso: Texto | None = None
    turma_id: int | None = None
    status: StatusAluno | None = None

    @field_validator("data_nascimento")
    @classmethod
    def validar_data_nascimento(cls, valor: date | None) -> date | None:
        return _nao_futura(valor)


class AlunoLeitura(Saida):
    id: int
    matricula: str
    nome_completo: str
    cpf: str | None
    email: str
    telefone: str | None
    data_nascimento: date | None
    curso: str
    turma_id: int
    status: str

    @field_serializer("cpf")
    def _mascarar(self, cpf: str | None) -> str | None:
        return mascarar_cpf(cpf)


class AlunoDetalhado(AlunoLeitura):
    """Consulta integrada do aluno (RF04): cadastro, disciplinas, notas e frequência."""

    inscricoes: list[InscricaoDetalhada]
