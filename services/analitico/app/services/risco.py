"""Serviço de risco acadêmico (RF07, D04, D06, D08, D09, D11).

Esqueleto. Na Fase 2 este módulo deve:
1. buscar as avaliações e frequências da inscrição na API interna do acadêmico;
2. calcular média e frequência com Decimal, arredondando antes de classificar (D06);
3. gravar um novo ResultadoRisco só se a classificação mudou (D11).

O cálculo em si deve ficar em funções puras (recebem números, devolvem resultado),
para ser testado sem banco e sem rede.
"""

import logging

logger = logging.getLogger("analitico.risco")


def recalcular_risco_da_inscricao(inscricao_id: int) -> None:
    logger.info("recalculo de risco solicitado", extra={"dados": {"inscricao_id": inscricao_id}})
