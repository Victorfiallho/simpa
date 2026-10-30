"""Perfil do usuário (dados pessoais e foto): validação, privacidade e quem vê o quê."""

import pytest

from app.core import seguranca
from tests.test_usuarios import SENHA, cliente, sessoes  # noqa: F401

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBP" + b"\x00" * 64


def cab(role="professor", usuario_id=3, **extras):
    token = seguranca.criar_token(usuario_id, role, "Fulano", **extras)
    return {"Authorization": f"Bearer {token}"}


def ana() -> dict:
    """prof.ana é o terceiro usuário demo. O token sai na hora, com a chave do teste."""
    return cab("professor", 3)


def ver(http, cabecalho=None):
    return http.get("/me", headers=cabecalho or ana()).json()["dados"]


def atualizar(http, corpo, cabecalho=None):
    return http.patch("/me", json=corpo, headers=cabecalho or ana())


# ---------- Acesso ----------


def test_sem_token_e_401(cliente):  # noqa: F811
    assert cliente.get("/me").status_code == 401
    assert cliente.patch("/me", json={}).status_code == 401
    assert cliente.put("/me/foto", content=JPEG).status_code == 401
    assert cliente.get("/me/foto").status_code == 401


def test_perfil_vazio_na_primeira_vez(cliente):  # noqa: F811
    perfil = ver(cliente)

    assert (perfil["usuario_id"], perfil["nome_usuario"], perfil["role"]) == (
        3,
        "prof.ana",
        "professor",
    )
    assert perfil["tem_foto"] is False
    assert perfil["preenchimento_percentual"] == 0


def test_usuario_inexistente_no_token_e_404(cliente):  # noqa: F811
    assert cliente.get("/me", headers=cab("professor", 999)).status_code == 404


# ---------- Dados pessoais ----------


def test_atualiza_so_os_campos_enviados(cliente):  # noqa: F811
    atualizar(cliente, {"telefone": "(62) 99999-1234", "cidade": "Anápolis", "uf": "go"})
    resposta = atualizar(cliente, {"bairro": "Centro"})

    perfil = resposta.json()["dados"]
    assert resposta.status_code == 200
    assert (perfil["telefone"], perfil["cidade"], perfil["uf"], perfil["bairro"]) == (
        "62999991234",
        "Anápolis",
        "GO",
        "Centro",
    )


def test_null_limpa_o_campo(cliente):  # noqa: F811
    atualizar(cliente, {"cidade": "Anápolis"})

    perfil = atualizar(cliente, {"cidade": None}).json()["dados"]

    assert perfil["cidade"] is None


def test_cpf_so_aparece_mascarado(cliente):  # noqa: F811
    corpo = atualizar(cliente, {"cpf": "529.982.247-25"}).json()

    assert corpo["dados"]["cpf"] == "***.982.247-**"
    assert "52998224725" not in str(corpo)
    assert "52998224725" not in str(ver(cliente))


def test_percentual_de_preenchimento(cliente):  # noqa: F811
    perfil = atualizar(
        cliente,
        {
            "nascimento": "1990-05-10",
            "cpf": "52998224725",
            "telefone": "62999991234",
            "email_contato": "ana@exemplo.com",
        },
    ).json()["dados"]

    assert perfil["preenchimento_percentual"] == 31  # 4 de 13 campos


@pytest.mark.parametrize(
    "corpo",
    [
        {"cpf": "111.111.111-11"},
        {"cpf": "123"},
        {"cpf": "529.982.247-26"},
        {"telefone": "123"},
        {"emergencia_telefone": "abc"},
        {"cep": "123"},
        {"uf": "XX"},
        {"nascimento": "2999-01-01"},
        {"nascimento": "1800-01-01"},
        {"email_contato": "sem-arroba"},
        {"cidade": ""},
        {"nome_completo": "x" * 81},
        {"campo_inexistente": "x"},
    ],
)
def test_dados_invalidos_sao_422(cliente, corpo):  # noqa: F811
    resposta = atualizar(cliente, corpo)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "VALIDACAO"


@pytest.mark.parametrize(
    "texto",
    ["<script>alert(1)</script>", "Rua <b>A</b>", "a > b", "linha\x00nula", "tab\x07"],
)
def test_texto_com_html_ou_controle_e_recusado(cliente, texto):  # noqa: F811
    assert atualizar(cliente, {"rua": texto}).status_code == 422


def test_espacos_extras_sao_normalizados(cliente):  # noqa: F811
    perfil = atualizar(cliente, {"rua": "  Rua   das   Flores "}).json()["dados"]

    assert perfil["rua"] == "Rua das Flores"


def test_cada_usuario_so_altera_o_proprio_perfil(cliente):  # noqa: F811
    atualizar(cliente, {"cidade": "Anápolis"}, cab("professor", 3))
    atualizar(cliente, {"cidade": "Goiânia"}, cab("professor", 4))

    assert ver(cliente, cab("professor", 3))["cidade"] == "Anápolis"
    assert ver(cliente, cab("professor", 4))["cidade"] == "Goiânia"


def test_o_corpo_nao_escolhe_de_quem_e_o_perfil(cliente):  # noqa: F811
    resposta = atualizar(cliente, {"usuario_id": 4, "cidade": "X"})

    assert resposta.status_code == 422  # campo não permitido


# ---------- Foto ----------


@pytest.mark.parametrize(
    ("imagem", "tipo"), [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")]
)
def test_envia_e_baixa_a_foto(cliente, imagem, tipo):  # noqa: F811
    resposta = cliente.put("/me/foto", content=imagem, headers=ana())

    assert resposta.status_code == 200
    assert resposta.json()["dados"]["tem_foto"] is True
    baixada = cliente.get("/me/foto", headers=ana())
    assert baixada.content == imagem
    assert baixada.headers["content-type"] == tipo
    assert baixada.headers["x-content-type-options"] == "nosniff"


def test_tipo_e_conferido_no_conteudo_e_nao_no_cabecalho(cliente):  # noqa: F811
    falsa = cliente.put(
        "/me/foto",
        content=b"<html><script>alert(1)</script></html>",
        headers=ana() | {"Content-Type": "image/png"},
    )

    assert falsa.status_code == 422
    assert falsa.json()["erro"]["codigo"] == "FOTO_INVALIDA"


def test_foto_vazia_e_recusada(cliente):  # noqa: F811
    resposta = cliente.put("/me/foto", content=b"", headers=ana())

    assert resposta.json()["erro"]["codigo"] == "FOTO_VAZIA"


def test_foto_acima_de_1mb_e_recusada(cliente):  # noqa: F811
    resposta = cliente.put("/me/foto", content=JPEG + b"\x00" * (1024 * 1024), headers=ana())

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "FOTO_GRANDE"


def test_remove_a_foto(cliente):  # noqa: F811
    cliente.put("/me/foto", content=PNG, headers=ana())

    resposta = cliente.delete("/me/foto", headers=ana())

    assert resposta.json()["dados"]["tem_foto"] is False
    assert cliente.get("/me/foto", headers=ana()).status_code == 404
    assert cliente.delete("/me/foto", headers=ana()).status_code == 200  # repetir não dá erro


def test_nova_foto_substitui_a_antiga(cliente):  # noqa: F811
    cliente.put("/me/foto", content=JPEG, headers=ana())
    cliente.put("/me/foto", content=PNG, headers=ana())

    assert cliente.get("/me/foto", headers=ana()).content == PNG


def test_foto_nao_vai_no_json_do_perfil(cliente):  # noqa: F811
    cliente.put("/me/foto", content=JPEG, headers=ana())

    assert "foto" not in {k for k in ver(cliente) if k != "tem_foto"}


def test_foto_de_outro_usuario_so_para_gestao_ou_o_dono(cliente):  # noqa: F811
    cliente.put("/me/foto", content=JPEG, headers=ana())

    assert cliente.get("/usuarios/3/foto", headers=ana()).status_code == 200
    assert cliente.get("/usuarios/3/foto", headers=cab("coordenador", 2)).status_code == 200
    assert cliente.get("/usuarios/3/foto", headers=cab("admin", 1)).status_code == 200
    negada = cliente.get("/usuarios/3/foto", headers=cab("professor", 4))
    assert negada.status_code == 403
    assert cliente.get("/usuarios/3/foto").status_code == 401


def test_aluno_tem_perfil_proprio_mas_nao_ve_foto_alheia(sessoes, cliente):  # noqa: F811
    from app.services import usuarios

    with sessoes() as db:
        aluno = usuarios.criar_usuario(db, "ana.aluna", "aluna@a.dev", SENHA, "aluno", aluno_id=8)
    dele = cab("aluno", aluno.id, aluno_id=8)
    cliente.put("/me/foto", content=PNG, headers=ana())

    assert ver(cliente, dele)["aluno_id"] == 8
    assert cliente.patch("/me", json={"cidade": "Anápolis"}, headers=dele).status_code == 200
    assert cliente.get("/usuarios/3/foto", headers=dele).status_code == 403
