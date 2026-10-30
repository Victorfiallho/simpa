"""Perfil aluno e pedidos de apoio (RF07): o aluno só vê o que é dele; a coordenação atende."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clientes import academico
from app.core import seguranca
from app.core.database import Base, get_db
from app.main import app
from tests.test_painel import inscricao

CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
MOTIVO = "Dificuldade com o conteúdo"


class _JwksFalso:
    def get_signing_key_from_jwt(self, _token):
        jwk = RSAAlgorithm.to_jwk(CHAVE.public_key(), as_dict=True)
        return jwt.PyJWK.from_dict({**jwk, "alg": "RS256"})


def token(sub="10", role="aluno", **extras) -> dict:
    payload = {
        "sub": sub,
        "role": role,
        "iss": "simpa-auth",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    } | extras
    return {"Authorization": f"Bearer {jwt.encode(payload, CHAVE, algorithm='RS256')}"}


ALUNA = token("10", aluno_id=1)  # Ana Lima
OUTRO = token("11", aluno_id=2)  # Bruno Costa
COORD = token("5", "coordenador")
PROF = token("3", "professor")


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setattr(seguranca, "_cliente_jwks", _JwksFalso)
    todas = [
        inscricao(1, 1, "Ana Lima", "EST", [("N1", "5.00", "4"), ("N2", "6.00", "6")]),
        inscricao(2, 1, "Ana Lima", "ALG", [("N1", "8.00", "4"), ("N2", "9.00", "6")]),
        inscricao(3, 2, "Bruno Costa", "EST", [("N1", "9.00", "4"), ("N2", "9.00", "6")]),
    ]
    monkeypatch.setattr(
        academico,
        "buscar_inscricoes",
        lambda *, aluno_id=None, **_: [i for i in todas if aluno_id in (None, i.aluno.id)],
    )
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessoes = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        with sessoes() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


def pedir(http, cabecalho=ALUNA, **alteracoes):
    corpo = {"motivo": MOTIVO, "texto": "Não entendi a matéria da N2."} | alteracoes
    return http.post("/meu/apoio", json=corpo, headers=cabecalho)


# ---------- Quem entra onde ----------


def test_aluno_ve_so_o_proprio_painel(http):
    painel = http.get("/meu/painel", headers=ALUNA).json()["dados"]

    assert [a["nome"] for a in painel["alunos"]] == ["Ana Lima"]
    assert painel["total_inscricoes"] == 2


def test_aluno_nao_escolhe_de_quem_e_o_painel(http):
    # O aluno_id vem do token; um parâmetro na URL não muda nada.
    painel = http.get("/meu/painel", params={"aluno_id": 2}, headers=ALUNA).json()["dados"]

    assert [a["nome"] for a in painel["alunos"]] == ["Ana Lima"]


@pytest.mark.parametrize(
    "rota",
    ["/painel", "/indicadores/turmas/1", "/predicao", "/relatorios/inscricoes", "/apoio"],
)
def test_token_de_aluno_nao_acessa_rotas_da_equipe(http, rota):
    assert http.get(rota, headers=ALUNA).status_code in (401, 403)


@pytest.mark.parametrize("cabecalho", [COORD, PROF])
def test_equipe_nao_usa_as_rotas_do_aluno(http, cabecalho):
    assert http.get("/meu/painel", headers=cabecalho).status_code == 401
    assert pedir(http, cabecalho).status_code == 401


def test_aluno_sem_aluno_id_no_token_e_recusado(http):
    assert http.get("/meu/painel", headers=token("10")).status_code == 401
    assert http.get("/meu/painel", headers=token("10", aluno_id="1")).status_code == 401
    assert http.get("/meu/painel", headers=token("10", aluno_id=True)).status_code == 401


def test_sem_token_e_401(http):
    assert http.get("/meu/painel").status_code == 401
    assert http.post("/meu/apoio", json={}).status_code == 401


# ---------- Pedir apoio ----------


def test_aluno_envia_pedido_de_apoio(http):
    resposta = pedir(http, disciplina_id=1)

    assert resposta.status_code == 201
    dados = resposta.json()["dados"]
    assert (dados["aluno_id"], dados["estado"], dados["disciplina_id"]) == (1, "recebida", 1)
    assert [h["estado"] for h in dados["historico"]] == ["recebida"]


def test_pedido_geral_sem_disciplina(http):
    assert pedir(http).status_code == 201


@pytest.mark.parametrize(
    ("alteracao", "status", "codigo"),
    [
        ({"disciplina_id": 99}, 422, "DISCIPLINA_NAO_INSCRITA"),
        ({"motivo": "Qualquer coisa"}, 422, "MOTIVO_INVALIDO"),
        ({"texto": "ab"}, 422, "VALIDACAO"),
        ({"texto": "x" * 201}, 422, "VALIDACAO"),
        ({"campo_extra": 1}, 422, "VALIDACAO"),
        ({"aluno_id": 2}, 422, "VALIDACAO"),  # não dá para pedir em nome de outro aluno
    ],
)
def test_pedido_invalido(http, alteracao, status, codigo):
    resposta = pedir(http, **alteracao)

    assert resposta.status_code == status
    assert resposta.json()["erro"]["codigo"] == codigo


def test_limite_de_cinco_pedidos_em_aberto(http):
    for _ in range(5):
        assert pedir(http).status_code == 201

    sexto = pedir(http)

    assert sexto.status_code == 409
    assert sexto.json()["erro"]["codigo"] == "LIMITE_DE_SOLICITACOES"
    assert pedir(http, OUTRO).status_code == 201  # o limite é por aluno


def test_concluir_libera_espaco_no_limite(http):
    ids = [pedir(http).json()["dados"]["id"] for _ in range(5)]
    http.put(f"/apoio/{ids[0]}/estado", json={"estado": "concluida"}, headers=COORD)

    assert pedir(http).status_code == 201


def test_aluno_lista_so_os_proprios_pedidos(http):
    pedir(http)
    pedir(http, OUTRO, texto="Preciso de ajuda com frequência")

    meus = http.get("/meu/apoio", headers=ALUNA).json()["dados"]

    assert len(meus) == 1
    assert meus[0]["aluno_id"] == 1


# ---------- Atendimento pela coordenação ----------


def test_coordenacao_ve_quem_pediu(http):
    pedir(http, disciplina_id=1)

    lista = http.get("/apoio", headers=COORD).json()["dados"]

    assert (lista[0]["aluno_nome"], lista[0]["matricula"]) == ("Ana Lima", "20260001")
    assert lista[0]["disciplina_nome"] == "Estatística"


def test_filtra_por_estado_e_mostra_os_mais_recentes_primeiro(http):
    primeiro = pedir(http, texto="Primeiro pedido").json()["dados"]["id"]
    pedir(http, texto="Segundo pedido")
    http.put(f"/apoio/{primeiro}/estado", json={"estado": "atendimento"}, headers=COORD)

    todos = http.get("/apoio", headers=COORD).json()["dados"]
    em_atendimento = http.get("/apoio", params={"estado": "atendimento"}, headers=COORD)

    assert [p["texto"] for p in todos] == ["Segundo pedido", "Primeiro pedido"]
    assert [p["id"] for p in em_atendimento.json()["dados"]] == [primeiro]


def test_mudar_estado_registra_o_historico_que_o_aluno_acompanha(http):
    pedido = pedir(http).json()["dados"]["id"]

    http.put(f"/apoio/{pedido}/estado", json={"estado": "atendimento"}, headers=COORD)
    http.put(f"/apoio/{pedido}/estado", json={"estado": "concluida"}, headers=COORD)

    meu = http.get("/meu/apoio", headers=ALUNA).json()["dados"][0]
    assert meu["estado"] == "concluida"
    assert [h["estado"] for h in meu["historico"]] == ["recebida", "atendimento", "concluida"]


def test_repetir_o_mesmo_estado_nao_duplica_o_historico(http):
    pedido = pedir(http).json()["dados"]["id"]

    http.put(f"/apoio/{pedido}/estado", json={"estado": "recebida"}, headers=COORD)

    assert len(http.get("/meu/apoio", headers=ALUNA).json()["dados"][0]["historico"]) == 1


@pytest.mark.parametrize("cabecalho", [PROF, ALUNA])
def test_so_gestao_atende(http, cabecalho):
    pedido = pedir(http).json()["dados"]["id"]

    resposta = http.put(f"/apoio/{pedido}/estado", json={"estado": "concluida"}, headers=cabecalho)

    assert resposta.status_code in (401, 403)


def test_estado_invalido_e_pedido_inexistente(http):
    pedido = pedir(http).json()["dados"]["id"]

    invalido = http.put(f"/apoio/{pedido}/estado", json={"estado": "feito"}, headers=COORD)
    inexistente = http.put("/apoio/999/estado", json={"estado": "concluida"}, headers=COORD)

    assert invalido.status_code == 422
    assert inexistente.status_code == 404
