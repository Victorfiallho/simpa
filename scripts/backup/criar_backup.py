"""Cria um backup cifrado e verificável do SIMPA (versão mínima: ver docs, etapa 7 não concluída).

Uso:
  python scripts/backup/criar_backup.py --chave /caminho/chave.b64 --saida /caminho/pasta

Consistência: "janela controlada". As APIs param (nenhuma escrita nova), a outbox e as filas
esvaziam, os workers param, e só então o dump é feito. Os serviços voltam no `finally`, mesmo se o
backup falhar. Os três bancos são lidos com a aplicação parada, então representam o mesmo instante.

O pacote é um .tar (bancos em formato custom do pg_dump, par de chaves do auth, manifesto) cifrado
com AES-256-GCM (cripto.py). O arquivo é escrito como `.parcial` e renomeado só no fim; um pacote
que já existe nunca é sobrescrito.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import cripto
from ambiente import BANCOS, FORMATO_DO_PACOTE, RAIZ, Compose, OperacaoError, ler_env

APIS = ("auth", "academico", "analitico")
WORKERS = ("academico-despachante", "auth-worker", "analitico-worker")
FILAS_PRINCIPAIS = ("analitico.recalculo-risco", "auth.auditoria")
PRAZO_DE_ESVAZIAR = 120


def _commit() -> str:
    try:
        saida = subprocess.run(  # noqa: S603 - comando fixo
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=RAIZ,
            check=True,
        )
        return saida.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "desconhecido"


def _mensagens_nas_filas(c: Compose) -> dict[str, int]:
    saida = c.rodar(
        "exec", "-T", "rabbitmq", "rabbitmqctl", "list_queues", "name", "messages", "--quiet"
    )
    filas: dict[str, int] = {}
    for linha in saida.stdout.decode().splitlines()[1:]:
        partes = linha.split()
        if len(partes) == 2 and partes[1].isdigit():
            filas[partes[0]] = int(partes[1])
    return filas


def _esvaziar(c: Compose) -> None:
    """Espera a outbox publicar tudo e as filas principais serem consumidas."""
    limite = time.monotonic() + PRAZO_DE_ESVAZIAR
    while True:
        pendentes = int(
            c.sql("academico_db", "select count(*) from evento_outbox where enviado_em is null")
        )
        filas = _mensagens_nas_filas(c)
        nas_filas = sum(filas.get(f, 0) for f in FILAS_PRINCIPAIS)
        if pendentes == 0 and nas_filas == 0:
            return
        if time.monotonic() > limite:
            raise OperacaoError(
                f"a janela não esvaziou em {PRAZO_DE_ESVAZIAR}s "
                f"(outbox pendente: {pendentes}, mensagens nas filas: {nas_filas})"
            )
        time.sleep(2)


def criar(c: Compose, chave: bytes, pasta_de_saida: Path) -> tuple[Path, dict]:
    pasta_de_saida.mkdir(parents=True, exist_ok=True)
    env = ler_env(c.env)
    inicio = time.monotonic()
    criado_em = datetime.now(UTC)
    nome = f"simpa-{criado_em:%Y%m%dT%H%M%SZ}.backup"
    final = pasta_de_saida / nome
    parcial = pasta_de_saida / (nome + ".parcial")
    if final.exists() or parcial.exists():
        raise OperacaoError(f"{final} já existe; backups nunca são sobrescritos")

    with tempfile.TemporaryDirectory(prefix="simpa-backup-") as tmp:
        trabalho = Path(tmp)
        arquivos: dict[str, str] = {}
        parados: list[str] = []
        try:
            c.rodar("stop", *APIS)
            parados += APIS
            _esvaziar(c)
            c.rodar("stop", *WORKERS)
            parados += WORKERS
            filas = _mensagens_nas_filas(c)
            janela_ate = time.monotonic()

            versoes = {
                s: c.sql(b, "select version_num from alembic_version") for s, b in BANCOS.items()
            }
            for banco in BANCOS.values():
                dump = c.rodar(
                    "exec",
                    "-T",
                    "postgres",
                    "sh",
                    "-c",
                    f'pg_dump -U "$POSTGRES_USER" -Fc --no-owner {banco}',
                ).stdout
                (trabalho / f"{banco}.dump").write_bytes(dump)
            globais = c.rodar(
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'pg_dumpall -U "$POSTGRES_USER" --globals-only',
            ).stdout
            (trabalho / "globais.sql").write_bytes(globais)
            chaves = c.rodar(
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "auth",
                "sh",
                "-c",
                "tar cf - -C /servico/chaves .",
            ).stdout
            (trabalho / "chaves-auth.tar").write_bytes(chaves)
            versao_pg = c.sql("postgres", "show server_version")
        finally:
            if parados:
                # Volta ao normal mesmo com erro: um backup que falha não pode derrubar o serviço.
                c.rodar("start", *parados, check=False)
        janela_s = time.monotonic() - janela_ate  # tempo desde o fim do esvaziamento

        for arq in sorted(trabalho.iterdir()):
            arquivos[arq.name] = cripto.sha256_do_arquivo(arq)
        manifesto = {
            "formato": FORMATO_DO_PACOTE,
            "criado_em_utc": criado_em.isoformat(),
            "commit": _commit(),
            "postgres": versao_pg,
            "projeto_de_origem": c.projeto,
            "consistencia": "janela controlada: APIs, despachante e workers parados durante o dump",
            "alembic": versoes,
            "arquivos": arquivos,
            "filas_na_janela": filas,
            "segredos": "nenhum valor de senha ou token no manifesto; a chave fica fora do pacote",
            "usuario_postgres": env.get("POSTGRES_USER", ""),
        }
        (trabalho / "manifesto.json").write_text(
            json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        tar = trabalho / "pacote.tar"
        with tarfile.open(tar, "w") as t:
            for arq in sorted(trabalho.iterdir()):
                if arq != tar:
                    t.add(arq, arcname=arq.name)
        try:
            cripto.cifrar_arquivo(chave, tar, parcial)
            parcial.rename(final)
        except BaseException:
            parcial.unlink(missing_ok=True)
            raise
    manifesto["pacote_sha256"] = cripto.sha256_do_arquivo(final)
    manifesto["duracao_total_s"] = round(time.monotonic() - inicio, 1)
    manifesto["janela_sem_escrita_s"] = round(janela_s, 1)
    (pasta_de_saida / (nome + ".sha256")).write_text(f"{manifesto['pacote_sha256']}  {nome}\n")
    return final, manifesto


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--chave", type=Path, required=True, help="arquivo da chave (base64, 0600)")
    ap.add_argument("--saida", type=Path, required=True, help="pasta dos backups")
    ap.add_argument("--projeto", default="simpa-test")
    ap.add_argument("--compose", type=Path, default=RAIZ / "compose.test.yml")
    ap.add_argument("--env", type=Path, default=RAIZ / ".env.test")
    a = ap.parse_args()
    try:
        final, manifesto = criar(
            Compose(a.projeto, a.compose, a.env), cripto.ler_chave(a.chave), a.saida
        )
    except (OperacaoError, cripto.CriptografiaError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "pacote": str(final),
                **{
                    k: manifesto[k]
                    for k in (
                        "criado_em_utc",
                        "pacote_sha256",
                        "duracao_total_s",
                        "janela_sem_escrita_s",
                    )
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
