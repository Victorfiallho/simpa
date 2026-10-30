"""Bloqueio do login após erros seguidos (RF09, RNF04)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.excecoes import MuitasTentativas
from app.models import BloqueioLogin
from app.services import bloqueio
from tests.test_usuarios import SENHA, cliente, entrar, sessoes  # noqa: F401

EMAIL = "ana.prof@simpa.dev"


def errar(http, vezes, email=EMAIL):
    return [entrar(http, email, "senha-errada").status_code for _ in range(vezes)]


def test_quinto_erro_ainda_e_401_e_o_seguinte_e_429(cliente):  # noqa: F811
    assert errar(cliente, 5) == [401] * 5

    bloqueada = entrar(cliente, EMAIL, "senha-errada")

    assert bloqueada.status_code == 429
    assert bloqueada.json()["erro"]["codigo"] == "MUITAS_TENTATIVAS"
    assert int(bloqueada.headers["Retry-After"]) in range(1, 61)


def test_senha_certa_tambem_e_recusada_durante_o_bloqueio(cliente):  # noqa: F811
    errar(cliente, 5)

    assert entrar(cliente, EMAIL, SENHA).status_code == 429


def test_login_correto_zera_a_contagem(cliente):  # noqa: F811
    errar(cliente, 4)
    assert entrar(cliente, EMAIL, SENHA).status_code == 200

    assert errar(cliente, 4) == [401] * 4  # recomeçou do zero
    assert entrar(cliente, EMAIL, SENHA).status_code == 200


def test_email_inexistente_tambem_bloqueia_sem_revelar_nada(cliente):  # noqa: F811
    assert errar(cliente, 5, "ninguem@simpa.dev") == [401] * 5

    resposta = entrar(cliente, "ninguem@simpa.dev", "x")

    assert resposta.status_code == 429


def test_bloqueio_vale_por_email_e_ignora_maiusculas(cliente):  # noqa: F811
    errar(cliente, 5)

    assert entrar(cliente, EMAIL.upper(), SENHA).status_code == 429
    assert entrar(cliente, "bruno.prof@simpa.dev", SENHA).status_code == 200


def test_mensagem_do_401_continua_generica(cliente):  # noqa: F811
    inexistente = entrar(cliente, "ninguem@simpa.dev", "x").json()["mensagem"]
    senha_errada = entrar(cliente, EMAIL, "x").json()["mensagem"]

    assert inexistente == senha_errada


def test_tabela_nao_guarda_o_email(sessoes, cliente):  # noqa: F811
    errar(cliente, 2)

    with sessoes() as db:
        linha = db.scalar(select(BloqueioLogin))
    assert linha.falhas == 2
    assert "ana" not in linha.chave
    assert len(linha.chave) == 64


def test_bloqueio_acaba_depois_do_tempo(sessoes, cliente):  # noqa: F811
    errar(cliente, 5)
    depois = datetime.now(UTC) + timedelta(seconds=get_settings().login_bloqueio_segundos + 1)

    with sessoes() as db:
        bloqueio.garantir_liberado(db, EMAIL, agora=depois)  # não levanta
        with pytest.raises(MuitasTentativas):
            bloqueio.garantir_liberado(db, EMAIL)

        # Um novo erro depois do prazo recomeça a contagem em 1, sem bloquear de novo.
        bloqueio.registrar_falha(db, EMAIL, agora=depois)
        db.commit()
        linha = db.scalar(select(BloqueioLogin))
        assert (linha.falhas, linha.bloqueado_ate) == (1, None)


def test_limites_vem_da_configuracao(sessoes, cliente, monkeypatch):  # noqa: F811
    monkeypatch.setenv("LOGIN_MAX_TENTATIVAS", "2")
    get_settings.cache_clear()

    assert errar(cliente, 2) == [401, 401]
    assert entrar(cliente, EMAIL, "x").status_code == 429
