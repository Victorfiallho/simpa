"""Tipos comuns dos sinais de alerta (evita importação circular entre os sinais)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sinal:
    tipo: str
    nivel: str
    titulo: str
    detalhe: str
    acao: str
