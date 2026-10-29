"""Recalcula o risco de todas as inscrições de uma vez.

Uso: docker compose exec analitico python -m app.comandos.recalcular

Útil depois de importar dados ou de mudar uma regra de classificação. Respeita a D11:
só grava linha nova onde a classificação mudou.
"""

from app.clientes import academico
from app.core.database import get_sessionmaker
from app.services.risco import registrar


def main() -> None:
    inscricoes = academico.buscar_inscricoes()
    with get_sessionmaker()() as db:
        gravadas = sum(registrar(db, inscricao) is not None for inscricao in inscricoes)
    print(f"{len(inscricoes)} inscrições analisadas, {gravadas} com classificação nova gravada.")


if __name__ == "__main__":
    main()
