"""Apoio comum do backup e da restauração: chamadas ao Docker Compose de um projeto explícito."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BANCOS = {"auth": "auth_db", "academico": "academico_db", "analitico": "analitico_db"}
FORMATO_DO_PACOTE = "simpa-backup/1"


class OperacaoError(Exception):
    """Falha prevista: a mensagem diz o que aconteceu e o que fazer."""


def ler_env(arquivo: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores


@dataclass(frozen=True)
class Compose:
    projeto: str
    arquivo: Path
    env: Path

    def rodar(
        self,
        *args: str,
        entrada: bytes | None = None,
        check: bool = True,
        timeout: float = 600,
    ) -> subprocess.CompletedProcess[bytes]:
        comando = [
            "docker",
            "compose",
            "--env-file",
            str(self.env),
            "-p",
            self.projeto,
            "-f",
            str(self.arquivo),
            *args,
        ]
        resultado = subprocess.run(  # noqa: S603 - comando montado só com valores fixos
            comando, input=entrada, capture_output=True, timeout=timeout, check=False, cwd=RAIZ
        )
        if check and resultado.returncode != 0:
            raise OperacaoError(
                f"docker compose {' '.join(args)} falhou (código {resultado.returncode}): "
                f"{resultado.stderr.decode(errors='replace')[-800:]}"
            )
        return resultado

    def sql(self, banco: str, consulta: str) -> str:
        """Roda uma consulta no PostgreSQL do projeto e devolve a saída sem cabeçalhos."""
        saida = self.rodar(
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            f'psql -U "$POSTGRES_USER" -d {banco} -At -c "{consulta}"',
        )
        return saida.stdout.decode().strip()

    def heads_do_alembic(self, servico: str) -> str:
        """Versão de migração que a IMAGEM do serviço espera (cabeça do Alembic)."""
        saida = self.rodar("run", "--rm", "--no-deps", "-T", servico, "alembic", "heads")
        linhas = [ln for ln in saida.stdout.decode().splitlines() if "(head)" in ln]
        if len(linhas) != 1:
            raise OperacaoError(f"{servico}: esperava uma cabeça do Alembic, achei {len(linhas)}")
        return linhas[0].split()[0]
