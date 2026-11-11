"""Restaura um backup do SIMPA em um ambiente DESCARTÁVEL e vazio.

Uso:
  python scripts/backup/restaurar_backup.py PACOTE --chave CHAVE \\
      --confirmo-destino simpa-restore-test

O que ele recusa, antes de escrever qualquer coisa no destino:
- destino que não seja um projeto de teste/restauração (`simpa-test`, `simpa-restore-test*`), ou
  cujo nome não seja repetido em --confirmo-destino (o ambiente de desenvolvimento `simpa` e
  qualquer outro nunca são alvo);
- chave errada, pacote corrompido/truncado, arquivo com hash diferente do manifesto, tar com
  caminhos perigosos;
- banco de destino que já tenha tabelas;
- versão de migração do pacote diferente da esperada pelas imagens do destino.

Aplica cada banco com `pg_restore --single-transaction --exit-on-error`: ou entra inteiro ou nada.
Restaura também o par de chaves de assinatura do auth no volume do destino, para que os tokens e o
JWKS continuem válidos. Não sobe a aplicação: isso é papel de quem verifica (verificar_restauracao).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import cripto
from ambiente import BANCOS, FORMATO_DO_PACOTE, RAIZ, Compose, OperacaoError

DESTINOS_PERMITIDOS = re.compile(r"^simpa-(restore-)?test[a-z0-9-]*$")


def validar_destino(projeto: str, confirmacao: str) -> None:
    if not DESTINOS_PERMITIDOS.match(projeto):
        raise OperacaoError(
            f"destino '{projeto}' não é um ambiente descartável de teste/restauração; recusado"
        )
    if confirmacao != projeto:
        raise OperacaoError(
            f"repita o nome do destino em --confirmo-destino ({projeto}) para autorizar"
        )


def abrir_pacote(pacote: Path, chave: bytes, pasta: Path) -> dict:
    """Decifra, extrai com segurança e confere cada arquivo contra o manifesto."""
    tar = pasta / "pacote.tar"
    cripto.decifrar_arquivo(chave, pacote, tar)
    with tarfile.open(tar) as t:
        for membro in t.getmembers():
            nome = Path(membro.name)
            if (
                not membro.isfile()
                or nome.is_absolute()
                or ".." in nome.parts
                or len(nome.parts) != 1
            ):
                raise OperacaoError(f"pacote recusado: membro inesperado '{membro.name}'")
        t.extractall(pasta / "conteudo", filter="data")
    conteudo = pasta / "conteudo"
    manifesto_arq = conteudo / "manifesto.json"
    if not manifesto_arq.exists():
        raise OperacaoError("pacote sem manifesto")
    manifesto = json.loads(manifesto_arq.read_text(encoding="utf-8"))
    if manifesto.get("formato") != FORMATO_DO_PACOTE:
        raise OperacaoError(f"formato desconhecido: {manifesto.get('formato')}")
    for nome, esperado in manifesto["arquivos"].items():
        arq = conteudo / nome
        if not arq.exists() or cripto.sha256_do_arquivo(arq) != esperado:
            raise OperacaoError(f"arquivo '{nome}' ausente ou com hash diferente do manifesto")
    manifesto["_conteudo"] = str(conteudo)
    return manifesto


def restaurar(c: Compose, manifesto: dict) -> dict[str, float]:
    conteudo = Path(manifesto["_conteudo"])
    tempos: dict[str, float] = {}

    # 1. Versões: o pacote tem de ser da mesma versão de migração que as imagens do destino.
    for servico in BANCOS:
        esperada = c.heads_do_alembic(servico)
        do_pacote = manifesto["alembic"][servico]
        if esperada != do_pacote:
            raise OperacaoError(
                f"{servico}: o pacote está na migração {do_pacote}, mas a imagem do destino espera "
                f"{esperada}. Restaure com a versão do código que gerou o backup "
                f"(commit {manifesto['commit'][:8]})."
            )

    # 2. Destino: só PostgreSQL e RabbitMQ sobem; os bancos precisam estar vazios.
    c.rodar("up", "-d", "--wait", "postgres", "rabbitmq")
    for banco in BANCOS.values():
        tabelas = int(
            c.sql(
                banco, "select count(*) from information_schema.tables where table_schema='public'"
            )
        )
        if tabelas:
            raise OperacaoError(
                f"o banco {banco} do destino já tem {tabelas} tabelas; recusado, nada foi escrito. "
                "Use um destino novo: docker compose ... down -v"
            )

    # 3. Bancos, cada um em uma transação.
    for banco in BANCOS.values():
        inicio = time.monotonic()
        c.rodar(
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            f'pg_restore -U "$POSTGRES_USER" -d {banco} --no-owner '
            "--single-transaction --exit-on-error",
            entrada=(conteudo / f"{banco}.dump").read_bytes(),
        )
        tempos[banco] = round(time.monotonic() - inicio, 1)

    # 4. Chaves de assinatura no volume do destino (o auth ainda não subiu).
    inicio = time.monotonic()
    c.rodar(
        "run",
        "--rm",
        "--no-deps",
        "-T",
        "auth",
        "sh",
        "-c",
        "tar xf - -C /servico/chaves",
        entrada=(conteudo / "chaves-auth.tar").read_bytes(),
    )
    tempos["chaves"] = round(time.monotonic() - inicio, 1)
    return tempos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("pacote", type=Path)
    ap.add_argument("--chave", type=Path, required=True)
    ap.add_argument("--projeto", default="simpa-restore-test")
    ap.add_argument("--compose", type=Path, default=RAIZ / "compose.restore-test.yml")
    ap.add_argument("--env", type=Path, default=RAIZ / ".env.restore-test")
    ap.add_argument("--confirmo-destino", default="")
    a = ap.parse_args()
    inicio = time.monotonic()
    try:
        validar_destino(a.projeto, a.confirmo_destino)
        chave = cripto.ler_chave(a.chave)
        with tempfile.TemporaryDirectory(prefix="simpa-restore-") as tmp:
            manifesto = abrir_pacote(a.pacote, chave, Path(tmp))
            tempos = restaurar(Compose(a.projeto, a.compose, a.env), manifesto)
    except (OperacaoError, cripto.CriptografiaError) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "restaurado": a.projeto,
                "criado_em_utc": manifesto["criado_em_utc"],
                "tempos_s": tempos,
                "total_s": round(time.monotonic() - inicio, 1),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
