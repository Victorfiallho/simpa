"""Defesas nas entradas: texto livre, parâmetros repetidos e busca com LIKE (RNF04).

O ORM já manda os valores como parâmetros do SQL, então não há injeção de SQL. Aqui ficam as
defesas que o ORM não dá:

* texto livre não aceita `<` nem `>` nem caracteres de controle, para que nada que lembre HTML
  seja gravado e depois exibido a outro usuário;
* um parâmetro de query repetido (`?limite=5&limite=500`) é recusado, em vez de valer só o último;
* `%`, `_` e `\\` digitados numa busca valem como letras, não como curingas do LIKE.
"""

import re

from fastapi import Request

from app.core.excecoes import ErroDeDominio

_PROIBIDOS = re.compile(r"[<>\x00-\x08\x0b-\x1f\x7f]")


def texto_seguro(valor: str) -> str:
    """Valida texto livre: sem `<`, `>` ou controle; espaços repetidos viram um só."""
    if _PROIBIDOS.search(valor):
        raise ValueError("Use apenas texto, sem os caracteres < e > nem caracteres de controle.")
    return re.sub(r"\s+", " ", valor).strip()


def escapar_like(termo: str) -> str:
    """Escapa os curingas do LIKE. Use com `.ilike(padrao, escape="\\\\")`."""
    return termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ParametroRepetido(ErroDeDominio):
    status_http = 400
    codigo = "PARAMETRO_REPETIDO"


def sem_parametros_repetidos(request: Request) -> None:
    """Dependência global: cada parâmetro de query só pode aparecer uma vez."""
    chaves = [chave for chave, _ in request.query_params.multi_items()]
    repetidas = sorted({chave for chave in chaves if chaves.count(chave) > 1})
    if repetidas:
        raise ParametroRepetido(f"Parâmetro repetido na consulta: {', '.join(repetidas)}.")
