"""Cliente da API interna do serviço auth (D13, D14).

O professor de uma disciplina mora no banco do auth, então a existência e o perfil dele
são conferidos por HTTP na rede interna do Docker.
"""

import httpx

from app.core.config import get_settings
from app.core.excecoes import RegraDeNegocioViolada, ServicoIndisponivel


def validar_professor(professor_id: int) -> None:
    """Garante que o id é de um usuário ativo com perfil professor (D03)."""
    url = f"{get_settings().auth_url}/internal/usuarios/{professor_id}"
    try:
        resposta = httpx.get(url, timeout=5)
    except httpx.HTTPError as erro:
        raise ServicoIndisponivel(
            "Não foi possível consultar o serviço de autenticação. Tente novamente."
        ) from erro

    if resposta.status_code == 404:
        raise RegraDeNegocioViolada(
            f"Professor {professor_id} não encontrado.", codigo="PROFESSOR_INVALIDO"
        )
    if resposta.status_code != 200:
        raise ServicoIndisponivel("O serviço de autenticação respondeu com erro.")

    usuario = resposta.json()["dados"]
    if usuario["role"] != "professor" or not usuario["ativo"]:
        raise RegraDeNegocioViolada(
            f"O usuário {professor_id} não é um professor ativo.", codigo="PROFESSOR_INVALIDO"
        )
