"""Contrato entre o front e o backend: os VALORES permitidos têm de ser os mesmos (RNF03, RF10).

Já houve divergência: os quatro motivos de apoio da tela eram todos inválidos para o backend e
nenhum aluno conseguia enviar o pedido. Cada lado era testado sozinho, e a conferência de contrato
olhava os nomes dos campos, não os valores. Este teste lê as constantes do TypeScript e as do
backend e falha se uma lista tiver um valor que a outra não tem.

Não precisa do ambiente no ar. Cada serviço roda no próprio processo, porque os três têm um pacote
`app` com o mesmo nome e não podem ser importados juntos.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend/src"

# ---------- Leitura do TypeScript ----------


def _texto(arquivo: str) -> str:
    return (FRONT / arquivo).read_text(encoding="utf-8")


def uniao(arquivo: str, nome: str) -> set[str]:
    """Valores de `type Nome = 'a' | 'b';`."""
    achado = re.search(rf"type {nome}\s*=\s*([^;]+);", _texto(arquivo))
    assert achado, f"type {nome} não encontrado em {arquivo}"
    return set(re.findall(r"'([^']+)'", achado.group(1)))


def lista(arquivo: str, nome: str) -> set[str]:
    """Textos de `const NOME = ['a', 'b']`."""
    achado = re.search(rf"const {nome}\b[^=]*=\s*\[(.*?)\];", _texto(arquivo), re.S)
    assert achado, f"const {nome} não encontrada em {arquivo}"
    return set(re.findall(r"'([^']+)'", achado.group(1)))


def primeiros_dos_pares(arquivo: str, nome: str) -> set[str]:
    """Primeiro texto de cada par em `const NOME = [['a', 'rótulo'], ...]`."""
    achado = re.search(rf"const {nome}\b[^=]*=\s*\[(.*?)\]\s*as const;", _texto(arquivo), re.S)
    assert achado, f"const {nome} não encontrada em {arquivo}"
    return set(re.findall(r"\[\s*'([^']+)'\s*,", achado.group(1)))


# ---------- Leitura do backend (um processo por serviço) ----------


def no_servico(servico: str, codigo: str) -> set[str]:
    """Roda `codigo` dentro do serviço; ele imprime um JSON com a lista de valores."""
    pasta = RAIZ / "services" / servico
    saida = subprocess.run(  # noqa: S603 - código fixo deste arquivo
        [sys.executable, "-c", codigo],
        cwd=pasta,
        env={"PATH": "", "PYTHONPATH": str(pasta), "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        check=True,
    )
    return set(json.loads(saida.stdout.strip().splitlines()[-1]))


def literais(modulo: str, nome: str) -> str:
    return (
        f"import json, typing; from {modulo} import {nome}; "
        f"print(json.dumps(list(typing.get_args({nome}))))"
    )


def tupla(modulo: str, nome: str) -> str:
    return f"import json; from {modulo} import {nome}; print(json.dumps(list({nome})))"


# Valores de um schema do OpenAPI: `enum` direto ou dentro de `anyOf` (campo opcional).
_VALORES = (
    "def valores(s):\n"
    "    achados = s.get('enum')\n"
    "    if achados is None:\n"
    "        achados = [e for a in s.get('anyOf', []) for e in a.get('enum', [])]\n"
    "    return achados\n"
)


def openapi_parametro(caminho: str, parametro: str) -> str:
    return (
        f"import json\n{_VALORES}from app.main import app\n"
        f"parametros = app.openapi()['paths']['{caminho}']['get']['parameters']\n"
        f"alvo = [p for p in parametros if p['name'] == '{parametro}'][0]['schema']\n"
        "print(json.dumps(valores(alvo)))"
    )


def openapi_schema(esquema: str, campo: str) -> str:
    return (
        f"import json\n{_VALORES}from app.main import app\n"
        f"schema = app.openapi()['components']['schemas']['{esquema}']['properties']['{campo}']\n"
        "print(json.dumps(valores(schema)))"
    )


# (descrição, valores do front, serviço, código que lista os valores do backend)
CASOS = [
    (
        "motivos do pedido de apoio",
        lambda: lista("paginas/MeuApoio.tsx", "MOTIVOS"),
        "analitico",
        tupla("app.models.apoio", "MOTIVOS_APOIO"),
    ),
    (
        "estados do pedido de apoio",
        lambda: uniao("api/tipos.ts", "EstadoApoio"),
        "analitico",
        tupla("app.models.apoio", "ESTADOS_APOIO"),
    ),
    (
        "tipo de alerta",
        lambda: uniao("api/tipos.ts", "TipoAlerta"),
        "analitico",
        openapi_parametro("/alertas", "tipo"),
    ),
    (
        "nível de alerta",
        lambda: uniao("api/tipos.ts", "NivelAlerta"),
        "analitico",
        openapi_parametro("/alertas", "nivel"),
    ),
    (
        "estado do atendimento do alerta",
        lambda: uniao("api/tipos.ts", "EstadoAtendimento"),
        "analitico",
        openapi_parametro("/alertas", "estado"),
    ),
    (
        "tipo de acompanhamento",
        lambda: uniao("api/tipos.ts", "TipoAcompanhamento"),
        "analitico",
        openapi_schema("AcompanhamentoEntrada", "tipo"),
    ),
    (
        "base do cenário",
        lambda: uniao("api/tipos.ts", "BaseCenario"),
        "analitico",
        openapi_parametro("/cenarios/projecao", "base"),
    ),
    (
        "situação de risco (filtro do relatório)",
        lambda: uniao("api/tipos.ts", "Situacao"),
        "analitico",
        openapi_parametro("/relatorios/inscricoes", "situacao"),
    ),
    (
        "janela dos indicadores",
        lambda: uniao("paginas/Analises.tsx", "Janela"),
        "analitico",
        openapi_parametro("/indicadores/turmas/{turma_id}", "janela"),
    ),
    (
        "formato do relatório",
        lambda: uniao("paginas/Relatorios.tsx", "Formato"),
        "analitico",
        openapi_parametro("/relatorios/inscricoes", "formato"),
    ),
    (
        "perfis de acesso",
        lambda: uniao("api/tipos.ts", "Role"),
        "auth",
        tupla("app.models.usuario", "ROLES"),
    ),
    (
        "status da turma",
        lambda: lista("paginas/Cadastros.tsx", "STATUS_TURMA"),
        "academico",
        literais("app.schemas.turma", "StatusTurma"),
    ),
    (
        "status da disciplina (a tela usa a mesma lista da turma)",
        lambda: lista("paginas/Cadastros.tsx", "STATUS_TURMA"),
        "academico",
        literais("app.schemas.disciplina", "StatusDisciplina"),
    ),
    (
        "status do aluno",
        lambda: lista("paginas/Cadastros.tsx", "STATUS_ALUNO"),
        "academico",
        literais("app.schemas.aluno", "StatusAluno"),
    ),
    (
        "status da inscrição",
        lambda: lista("paginas/Cadastros.tsx", "STATUS_INSCRICAO"),
        "academico",
        literais("app.schemas.inscricao", "StatusInscricao"),
    ),
    (
        "turno da turma",
        lambda: lista("paginas/Cadastros.tsx", "TURNOS"),
        "academico",
        literais("app.schemas.turma", "Turno"),
    ),
    (
        "tipo da avaliação",
        lambda: primeiros_dos_pares("paginas/Lancamentos.tsx", "TIPOS"),
        "academico",
        tupla("app.models.avaliacao", "TIPOS_AVALIACAO"),
    ),
]


@pytest.mark.parametrize(
    ("descricao", "do_front", "servico", "codigo"), CASOS, ids=[c[0] for c in CASOS]
)
def test_valores_do_front_sao_os_do_backend(descricao, do_front, servico, codigo):
    front = do_front()
    backend = no_servico(servico, codigo)

    assert front, f"nenhum valor lido do front para: {descricao}"
    assert backend, f"nenhum valor lido do backend para: {descricao}"
    assert front == backend, (
        f"{descricao}: o front e o backend divergem.\n"
        f"  só no front:   {sorted(front - backend)}\n"
        f"  só no backend: {sorted(backend - front)}"
    )
