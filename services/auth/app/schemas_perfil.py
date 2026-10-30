"""Schemas do perfil do usuário (dados pessoais e foto).

Texto livre não aceita `<` nem `>` nem caracteres de controle, para que nada que lembre HTML
seja gravado e depois exibido por outro usuário (RNF04).
"""

import re
from datetime import date
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_serializer,
)

UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


def _cpf_valido(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        raise ValueError("CPF inválido.")
    for tamanho in (9, 10):
        pesos = range(tamanho + 1, 1, -1)
        soma = sum(int(d) * peso for d, peso in zip(digitos[:tamanho], pesos, strict=True))
        if (soma * 10) % 11 % 10 != int(digitos[tamanho]):
            raise ValueError("CPF inválido: dígito verificador não confere.")
    return digitos


def mascarar_cpf(cpf: str | None) -> str | None:
    """Só os 6 dígitos do meio aparecem nas respostas (RNF04): ***.456.789-**"""
    return None if cpf is None else f"***.{cpf[3:6]}.{cpf[6:9]}-**"


def _texto_seguro(valor: str) -> str:
    if re.search(r"[<>]", valor) or re.search(r"[\x00-\x08\x0b-\x1f\x7f]", valor):
        raise ValueError("Use apenas texto, sem os caracteres < e > nem caracteres de controle.")
    return re.sub(r"\s+", " ", valor).strip()


def _so_digitos(tamanhos: tuple[int, ...], nome: str):
    def validar(valor: str) -> str:
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) not in tamanhos:
            esperado = " ou ".join(str(t) for t in tamanhos)
            raise ValueError(f"{nome} deve ter {esperado} dígitos.")
        return digitos

    return validar


def _uf_valida(valor: str) -> str:
    valor = valor.upper()
    if valor not in UFS:
        raise ValueError("UF inválida.")
    return valor


def _nascimento_valido(valor: date) -> date:
    if not (date(1900, 1, 1) <= valor <= date.today()):
        raise ValueError("Data de nascimento inválida.")
    return valor


def _texto(maximo: int):
    return Annotated[
        str, StringConstraints(min_length=1, max_length=maximo), AfterValidator(_texto_seguro)
    ]


CPF = Annotated[str, AfterValidator(_cpf_valido)]
Telefone = Annotated[str, AfterValidator(_so_digitos((10, 11), "O telefone"))]
CEP = Annotated[str, AfterValidator(_so_digitos((8,), "O CEP"))]
UF = Annotated[str, AfterValidator(_uf_valida)]
Nascimento = Annotated[date, AfterValidator(_nascimento_valido)]


class PerfilAtualizacao(BaseModel):
    """PATCH: só os campos enviados mudam; `null` limpa o campo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome_completo: _texto(80) | None = None
    cargo: _texto(60) | None = None
    matricula_funcional: _texto(20) | None = None
    nascimento: Nascimento | None = None
    cpf: CPF | None = None
    telefone: Telefone | None = None
    email_contato: EmailStr | None = None
    cep: CEP | None = None
    rua: _texto(100) | None = None
    numero: _texto(10) | None = None
    complemento: _texto(60) | None = None
    bairro: _texto(60) | None = None
    cidade: _texto(60) | None = None
    uf: UF | None = None
    emergencia_nome: _texto(80) | None = None
    emergencia_parentesco: _texto(40) | None = None
    emergencia_telefone: Telefone | None = None


class PerfilSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    nome_usuario: str
    role: str
    aluno_id: int | None
    nome_completo: str | None = None
    cargo: str | None = None
    matricula_funcional: str | None = None
    nascimento: date | None = None
    cpf: str | None = None
    telefone: str | None = None
    email_contato: str | None = None
    cep: str | None = None
    rua: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    emergencia_nome: str | None = None
    emergencia_parentesco: str | None = None
    emergencia_telefone: str | None = None
    tem_foto: bool = False
    preenchimento_percentual: int = 0

    @field_serializer("cpf")
    def _mascarar(self, cpf: str | None) -> str | None:
        return mascarar_cpf(cpf)
