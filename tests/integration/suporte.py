"""Apoio dos testes entre serviços: HTTP real no gateway, espera por condição e controle do Compose.

Nada aqui importa os pacotes `app` dos serviços (os três têm o mesmo nome). Tudo passa pelos
contratos HTTP, pelo broker e pelos comandos do Compose do projeto `simpa-test`.
"""

from __future__ import annotations

import csv
import io
import json
import os
import secrets
import subprocess
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

RAIZ = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("SIMPA_BASE_URL", "http://127.0.0.1:18080")
ARQUIVO_ENV = RAIZ / ".env.test"
PROJETO = "simpa-test"
ARQUIVO_COMPOSE = RAIZ / "compose.test.yml"

# Prazo inicial para o evento chegar ao histórico (meta a validar, não garantia do SIMPA).
PRAZO_EVENTO = float(os.environ.get("SIMPA_PRAZO_EVENTO", "15"))


def ler_env() -> dict[str, str]:
    """Lê o .env.test (sintético). Variáveis de ambiente com o mesmo nome têm prioridade."""
    valores: dict[str, str] = {}
    if ARQUIVO_ENV.exists():
        for linha in ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, _, valor = linha.partition("=")
                valores[chave.strip()] = valor.strip()
    return {**valores, **{k: v for k, v in os.environ.items() if k in valores}}


def compose(
    *args: str, timeout: float = 120, check: bool = True, entrada: str | None = None
) -> subprocess.CompletedProcess:
    """Roda `docker compose` sempre com o arquivo e o projeto de teste explícitos."""
    comando = [
        "docker", "compose", "--env-file", str(ARQUIVO_ENV),
        "-p", PROJETO, "-f", str(ARQUIVO_COMPOSE), *args,
    ]  # fmt: skip
    resultado = subprocess.run(  # noqa: S603 - comando fixo, sem entrada do usuário
        comando,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=RAIZ,
        input=entrada,
    )
    if check and resultado.returncode != 0:
        # Sem isto, o erro do Compose ficaria escondido dentro de `CalledProcessError`.
        raise RuntimeError(
            f"docker compose {' '.join(args)} falhou (código {resultado.returncode}):\n"
            f"{resultado.stdout[-1500:]}\n{resultado.stderr[-1500:]}"
        )
    return resultado


def saude_dos_servicos() -> dict[str, str]:
    """Saúde de cada serviço do projeto de teste (`healthy`, `unhealthy`, `starting` ou vazio)."""
    saida = compose("ps", "-a", "--format", "json").stdout
    return {
        item["Service"]: item.get("Health") or item.get("State", "")
        for item in (json.loads(linha) for linha in saida.splitlines() if linha.strip())
    }


def filas() -> dict[str, dict[str, int]]:
    """Mensagens e consumidores de cada fila do RabbitMQ de teste."""
    saida = compose(
        "exec", "-T", "rabbitmq", "rabbitmqctl", "list_queues", "name", "messages", "consumers"
    )
    resultado: dict[str, dict[str, int]] = {}
    for linha in saida.stdout.splitlines():
        partes = linha.split()
        if len(partes) == 3 and partes[1].isdigit() and partes[2].isdigit():
            resultado[partes[0]] = {"mensagens": int(partes[1]), "consumidores": int(partes[2])}
    return resultado


def unico() -> str:
    """Sufixo curto e aleatório: cada teste cria os próprios dados, sem depender da ordem."""
    return secrets.token_hex(4)


def matricula_unica() -> str:
    return "8" + str(secrets.randbelow(10**9)).zfill(9)


def esperar_ate(
    obter: Callable[[], Any],
    aceitar: Callable[[Any], bool],
    descricao: str,
    prazo: float = PRAZO_EVENTO,
    intervalo: float = 0.3,
) -> Any:
    """Consulta até a condição valer, sem espera fixa. Se o prazo estoura, o erro mostra o visto."""
    limite = time.monotonic() + prazo
    while True:
        ultimo = obter()
        if aceitar(ultimo):
            return ultimo
        if time.monotonic() > limite:
            raise AssertionError(
                f"Prazo de {prazo:.0f}s esgotado esperando: {descricao}.\n"
                f"Último valor observado: {ultimo!r}"
            )
        time.sleep(intervalo)


@dataclass
class Sessao:
    """Um usuário autenticado no gateway."""

    http: httpx.Client
    token: str | None
    usuario_id: int | None = None
    role: str | None = None

    def pedir(self, metodo: str, caminho: str, **kwargs: Any) -> httpx.Response:
        cabecalhos = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            cabecalhos["Authorization"] = f"Bearer {self.token}"
        return self.http.request(metodo, f"/api{caminho}", headers=cabecalhos, **kwargs)

    def get(self, caminho: str, **kw: Any) -> httpx.Response:
        return self.pedir("GET", caminho, **kw)

    def post(self, caminho: str, json: Any = None, **kw: Any) -> httpx.Response:
        return self.pedir("POST", caminho, json=json, **kw)

    def patch(self, caminho: str, json: Any = None, **kw: Any) -> httpx.Response:
        return self.pedir("PATCH", caminho, json=json, **kw)


def dados(resposta: httpx.Response, esperado: int = 200) -> Any:
    """Confere o status e devolve `dados` do envelope. A falha mostra a rota e o corpo."""
    assert resposta.status_code == esperado, (
        f"{resposta.request.method} {resposta.request.url.path} respondeu "
        f"{resposta.status_code} (esperado {esperado}): {resposta.text[:600]}"
    )
    return resposta.json()["dados"]


def entrar(http: httpx.Client, email: str, senha: str) -> Sessao:
    corpo = dados(http.post("/api/auth/login", json={"email": email, "senha": senha}))
    return Sessao(http, corpo["access_token"], corpo["usuario"]["id"], corpo["usuario"]["role"])


# ---------- Fábricas de dados (sempre pela API, com o schema real) ----------


def criar_turma(gestor: Sessao) -> dict:
    return dados(
        gestor.post(
            "/academico/turmas",
            {
                "nome": f"Turma teste {unico()}",
                "curso": "Inteligência Artificial",
                "periodo_letivo": "2026.2",
                "turno": "noturno",
            },
        ),
        201,
    )


def criar_disciplina(
    gestor: Sessao, turma_id: int, professor_id: int | None, nome: str | None = None
) -> dict:
    return dados(
        gestor.post(
            "/academico/disciplinas",
            {
                "nome": nome or f"Disciplina {unico()}",
                "carga_horaria": 60,
                "periodo_letivo": "2026.2",
                "turma_id": turma_id,
                "professor_id": professor_id,
            },
        ),
        201,
    )


def criar_aluno(gestor: Sessao, turma_id: int) -> dict:
    sufixo = unico()
    return dados(
        gestor.post(
            "/academico/alunos",
            {
                "matricula": matricula_unica(),
                "nome_completo": f"Aluno Teste {sufixo}",
                "email": f"aluno.{sufixo}@exemplo.com",
                "curso": "Inteligência Artificial",
                "turma_id": turma_id,
            },
        ),
        201,
    )


def inscrever(gestor: Sessao, aluno_id: int, disciplina_id: int) -> dict:
    return dados(
        gestor.post(
            "/academico/inscricoes", {"aluno_id": aluno_id, "disciplina_id": disciplina_id}
        ),
        201,
    )


def lancar_nota(
    quem: Sessao, inscricao_id: int, nota: str, periodo: str = "N1", peso: str = "4"
) -> dict:
    return dados(
        quem.post(
            "/academico/avaliacoes",
            {
                "inscricao_id": inscricao_id,
                "tipo_avaliacao": "prova",
                "periodo_avaliacao": periodo,
                "nota": nota,
                "peso": peso,
            },
        ),
        201,
    )


def lancar_frequencia(
    quem: Sessao, inscricao_id: int, faltas: int, periodo: str = "N1", aulas: int = 32
) -> dict:
    return dados(
        quem.post(
            "/academico/frequencias",
            {
                "inscricao_id": inscricao_id,
                "periodo_avaliacao": periodo,
                "aulas_previstas": aulas,
                "faltas": faltas,
            },
        ),
        201,
    )


def historico(quem: Sessao, inscricao_id: int) -> list[dict]:
    """Histórico de risco da inscrição, do mais antigo para o mais novo."""
    itens = dados(quem.get(f"/analitico/riscos/inscricoes/{inscricao_id}/historico"))
    return sorted(itens, key=lambda r: r["id"])


def estados(itens: list[dict]) -> list[str]:
    """Sequência de situações sem repetições vizinhas, para conferir transições."""
    sequencia: list[str] = []
    for item in itens:
        if not sequencia or sequencia[-1] != item["status"]:
            sequencia.append(item["status"])
    return sequencia


def ler_relatorio_csv(conteudo: bytes) -> list[dict[str, str]]:
    """Linhas de dados do relatório CSV (separador ';', com BOM e cabeçalho do relatório antes)."""
    linhas = list(csv.reader(io.StringIO(conteudo.decode("utf-8-sig")), delimiter=";"))
    posicao = next(i for i, linha in enumerate(linhas) if linha and linha[0] == "Matrícula")
    colunas = linhas[posicao]
    return [dict(zip(colunas, linha, strict=False)) for linha in linhas[posicao + 1 :] if linha]


# ---------- Banco, fila e broker (somente o ambiente de teste) ----------


def _sql(banco: str, consulta: str) -> str:
    """Roda uma consulta de LEITURA no PostgreSQL de teste e devolve a saída em texto simples."""
    resultado = compose(
        "exec", "-T", "-e", f"CONSULTA={consulta}", "postgres",
        "sh", "-c", f'psql -U "$POSTGRES_USER" -d {banco} -tAc "$CONSULTA"',
    )  # fmt: skip
    return resultado.stdout.strip()


def _padrao_da_inscricao(inscricao_id: int) -> str:
    return f'%"inscricao_id": {int(inscricao_id)}}}%'


def eventos_pendentes(inscricao_id: int) -> int:
    """Eventos da inscrição que ainda esperam na outbox do acadêmico."""
    consulta = (
        "SELECT count(*) FROM evento_outbox WHERE enviado_em IS NULL "  # noqa: S608
        f"AND corpo LIKE '{_padrao_da_inscricao(inscricao_id)}'"
    )
    return int(_sql("academico_db", consulta))


def ultimo_evento_enviado(inscricao_id: int) -> str:
    """Envelope JSON do evento mais recente da inscrição que o despachante já publicou."""
    consulta = (
        "SELECT corpo FROM evento_outbox WHERE enviado_em IS NOT NULL "  # noqa: S608
        f"AND corpo LIKE '{_padrao_da_inscricao(inscricao_id)}' ORDER BY criado_em DESC LIMIT 1"
    )
    return _sql("academico_db", consulta)


def total_processados() -> int:
    """Quantos eventos o worker do analítico já anotou como tratados."""
    return int(_sql("analitico_db", "SELECT count(*) FROM evento_processado"))


def foi_processado(event_id: str) -> bool:
    identificador = uuid.UUID(event_id)  # valida: só UUID entra na consulta
    consulta = f"SELECT count(*) FROM evento_processado WHERE event_id = '{identificador}'"  # noqa: S608
    return _sql("analitico_db", consulta) == "1"


PUBLICAR = """
import os, sys, pika
chave, corpo = sys.argv[1], sys.stdin.read()
with pika.BlockingConnection(pika.URLParameters(os.environ["RABBITMQ_URL"])) as c:
    canal = c.channel()
    canal.confirm_delivery()
    propriedades = pika.BasicProperties(delivery_mode=2)
    canal.basic_publish("simpa.eventos", chave, corpo.encode(), propriedades, mandatory=True)
"""


def publicar_no_broker(chave: str, corpo: str) -> None:
    """Publica uma mensagem crua na exchange de eventos (simula entrega repetida ou inválida)."""
    compose("exec", "-T", "analitico", "python", "-c", PUBLICAR, chave, entrada=corpo)


# ---------- Monitoramento (compose.monitoramento.yml, só se estiver de pé) ----------

PROMETHEUS = os.environ.get("SIMPA_PROMETHEUS_URL", "http://127.0.0.1:19090")
ALERTMANAGER = os.environ.get("SIMPA_ALERTMANAGER_URL", "http://127.0.0.1:19093")


def monitoramento_no_ar() -> bool:
    try:
        return httpx.get(f"{PROMETHEUS}/-/healthy", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def alertas_do_prometheus() -> list[dict]:
    """Alertas em estado `pending` ou `firing` agora, com os rótulos."""
    dados = httpx.get(f"{PROMETHEUS}/api/v1/alerts", timeout=10).json()["data"]["alerts"]
    return [{"nome": a["labels"]["alertname"], "estado": a["state"], **a["labels"]} for a in dados]


def disparado(nome: str, **rotulos: str) -> bool:
    """O alerta está `firing` com estes rótulos?"""
    return any(
        a["nome"] == nome
        and a["estado"] == "firing"
        and all(a.get(k) == v for k, v in rotulos.items())
        for a in alertas_do_prometheus()
    )


def alertas_inibidos() -> set[str]:
    """Nomes dos alertas que o Alertmanager recebeu mas manteve inibidos (consequência de outro)."""
    dados = httpx.get(f"{ALERTMANAGER}/api/v2/alerts", timeout=10).json()
    return {a["labels"]["alertname"] for a in dados if a["status"]["inhibitedBy"]}


def notificacoes_recebidas() -> list[dict]:
    """Tudo que o receptor LOCAL de teste recebeu do Alertmanager (nada sai para fora)."""
    script = (
        "import urllib.request; "
        "print(urllib.request.urlopen('http://localhost:8080/alertas', timeout=5).read().decode())"
    )
    saida = compose("exec", "-T", "receptor-alertas", "python", "-c", script).stdout
    return json.loads(saida)
