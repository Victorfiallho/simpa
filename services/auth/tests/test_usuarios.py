"""Login (RF09) e rota interna de usuários, num SQLite em memória."""

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import seguranca
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app
from app.models import Usuario
from app.services import usuarios

SENHA = "senha-de-teste-123"


@pytest.fixture
def sessoes(tmp_path, monkeypatch):
    monkeypatch.setenv("CHAVES_DIR", str(tmp_path))
    get_settings.cache_clear()
    seguranca.chave_privada.cache_clear()
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    yield fabrica
    engine.dispose()
    get_settings.cache_clear()
    seguranca.chave_privada.cache_clear()


@pytest.fixture
def cliente(sessoes):
    def _db():
        with sessoes() as db:
            yield db

    with sessoes() as db:
        usuarios.garantir_usuarios_demo(db, SENHA)
    app.dependency_overrides[get_db] = _db
    yield TestClient(app)
    app.dependency_overrides.clear()


def entrar(cliente, email, senha):
    return cliente.post("/login", json={"email": email, "senha": senha})


def test_login_devolve_token_valido(cliente):
    resposta = entrar(cliente, "ana.prof@simpa.dev", SENHA)

    dados = resposta.json()["dados"]
    assert resposta.status_code == 200
    assert dados["usuario"]["role"] == "professor"
    chave = jwt.PyJWK(cliente.get("/.well-known/jwks.json").json()["keys"][0]).key
    token = jwt.decode(dados["access_token"], chave, algorithms=["RS256"], issuer="simpa-auth")
    assert token["sub"] == str(dados["usuario"]["id"])


def test_email_nao_diferencia_maiusculas(cliente):
    assert entrar(cliente, "ADMIN@simpa.dev", SENHA).status_code == 200


@pytest.mark.parametrize(
    ("email", "senha"),
    [("admin@simpa.dev", "errada"), ("ninguem@simpa.dev", SENHA)],
    ids=["senha-errada", "email-inexistente"],
)
def test_login_invalido_tem_mensagem_generica(cliente, email, senha):
    resposta = entrar(cliente, email, senha)

    assert resposta.status_code == 401
    assert resposta.json()["mensagem"] == "E-mail ou senha inválidos."


def test_usuario_inativo_nao_entra(cliente, sessoes):
    with sessoes() as db:
        db.query(Usuario).filter_by(nome_usuario="prof.bruno").update({"ativo": False})
        db.commit()

    assert entrar(cliente, "bruno.prof@simpa.dev", SENHA).status_code == 401


def test_senha_e_gravada_como_hash(sessoes):
    with sessoes() as db:
        usuario = usuarios.criar_usuario(db, "novo", "novo@simpa.dev", SENHA, "professor")

    assert usuario.senha_hash != SENHA
    assert seguranca.senha_confere(SENHA, usuario.senha_hash)


def test_usuarios_demo_nao_sao_duplicados(sessoes):
    with sessoes() as db:
        usuarios.garantir_usuarios_demo(db, SENHA)
        usuarios.garantir_usuarios_demo(db, SENHA)
        assert db.query(Usuario).count() == len(usuarios.USUARIOS_DEMO)


def test_rota_interna_de_usuario(cliente):
    professores = cliente.get("/internal/usuarios", params={"role": "professor"}).json()["dados"]
    um = cliente.get(f"/internal/usuarios/{professores[0]['id']}").json()["dados"]

    assert len(professores) == 3
    assert um["role"] == "professor"
    assert cliente.get("/internal/usuarios/999").status_code == 404


# ---------- Perfil aluno (D03) ----------


def test_usuario_aluno_leva_o_cadastro_no_token(cliente, sessoes):
    with sessoes() as db:
        usuarios.criar_usuario(db, "ana.aluna", "ana.aluna@aluno.dev", SENHA, "aluno", aluno_id=42)

    resposta = entrar(cliente, "ana.aluna@aluno.dev", SENHA)

    dados = resposta.json()["dados"]
    assert dados["usuario"]["role"] == "aluno"
    assert dados["usuario"]["aluno_id"] == 42
    chave = jwt.PyJWK(cliente.get("/.well-known/jwks.json").json()["keys"][0]).key
    token = jwt.decode(dados["access_token"], chave, algorithms=["RS256"], issuer="simpa-auth")
    assert (token["role"], token["aluno_id"]) == ("aluno", 42)


def test_token_dos_outros_perfis_nao_tem_aluno_id(cliente):
    dados = entrar(cliente, "ana.prof@simpa.dev", SENHA).json()["dados"]

    chave = jwt.PyJWK(cliente.get("/.well-known/jwks.json").json()["keys"][0]).key
    token = jwt.decode(dados["access_token"], chave, algorithms=["RS256"], issuer="simpa-auth")
    assert "aluno_id" not in token


def test_aluno_sem_cadastro_e_recusado_pelo_banco(sessoes):
    from sqlalchemy.exc import IntegrityError

    with sessoes() as db, pytest.raises(IntegrityError):
        usuarios.criar_usuario(db, "sem.cadastro", "sem@aluno.dev", SENHA, "aluno")


def test_professor_com_aluno_id_e_recusado_pelo_banco(sessoes):
    from sqlalchemy.exc import IntegrityError

    with sessoes() as db, pytest.raises(IntegrityError):
        usuarios.criar_usuario(db, "p", "p@simpa.dev", SENHA, "professor", aluno_id=1)


def test_dois_usuarios_nao_dividem_o_mesmo_aluno(sessoes):
    from sqlalchemy.exc import IntegrityError

    with sessoes() as db:
        usuarios.criar_usuario(db, "a1", "a1@aluno.dev", SENHA, "aluno", aluno_id=7)
    with sessoes() as db, pytest.raises(IntegrityError):
        usuarios.criar_usuario(db, "a2", "a2@aluno.dev", SENHA, "aluno", aluno_id=7)


def test_usuario_aluno_demo_so_com_aluno_id(sessoes):
    with sessoes() as db:
        usuarios.garantir_usuarios_demo(db, SENHA)
        assert db.query(Usuario).filter_by(role="aluno").count() == 0
        usuarios.garantir_usuarios_demo(db, SENHA, aluno_id=5)
        usuarios.garantir_usuarios_demo(db, SENHA, aluno_id=5)
        assert db.query(Usuario).filter_by(role="aluno").count() == 1


def test_rota_interna_de_professores_nao_lista_alunos(cliente, sessoes):
    with sessoes() as db:
        usuarios.criar_usuario(db, "ana.aluna", "ana.aluna@aluno.dev", SENHA, "aluno", aluno_id=42)

    professores = cliente.get("/internal/usuarios", params={"role": "professor"}).json()["dados"]

    assert {p["role"] for p in professores} == {"professor"}
