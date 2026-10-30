"""Alertas precoces e acompanhamento (RF07): regras dos sinais e rotas da coordenação."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clientes import academico
from app.core.database import Base, get_db
from app.core.seguranca import UsuarioAtual, usuario_atual
from app.main import app
from app.services.alertas import sinal_de_frequencia, sinal_de_queda
from tests.test_painel import inscricao

# ---------- Regras dos sinais ----------


@pytest.mark.parametrize(
    ("n1", "n2", "nivel"),
    [
        ("8.00", "4.00", "alto"),  # 50%, partindo de nota boa
        ("8.00", "5.50", "alto"),  # 31%: acima de 30% partindo de N1 >= 7
        ("6.00", "3.50", "atencao"),  # 42%, N1 baixa
        ("8.00", "6.00", "atencao"),  # 25%: entre 20% e 30% com N1 >= 7
        ("8.00", "6.50", None),  # 18,75%: abaixo de 20%
        ("6.00", "4.50", None),  # 25% com N1 < 7: não dispara
        ("5.00", "4.50", None),
    ],
)
def test_sinal_de_queda(n1, n2, nivel):
    sinal = sinal_de_queda("Estatística", D(n1), D(n2))

    assert (sinal.nivel if sinal else None) == nivel


def test_queda_sem_as_duas_notas_nao_dispara():
    assert sinal_de_queda("EST", None, D("5")) is None
    assert sinal_de_queda("EST", D("5"), None) is None
    assert sinal_de_queda("EST", D("0"), D("0")) is None


def test_texto_da_queda():
    sinal = sinal_de_queda("Estatística", D("7.80"), D("4.50"))

    assert sinal.titulo == "Queda de 42% entre a N1 e a N2"
    assert sinal.detalhe == "Estatística: N1 7,80 → N2 4,50"


@pytest.mark.parametrize(
    ("faltas", "nivel", "titulo"),
    [
        (9, "alto", "Frequência abaixo de 75% (71,88%)"),
        (8, "alto", "Sem margem: a próxima falta reprova por frequência"),
        (7, "atencao", "Margem crítica: restam 1 falta(s)"),
        (6, "atencao", "Margem crítica: restam 2 falta(s)"),
        (5, None, None),
        (0, None, None),
    ],
)
def test_sinal_de_frequencia_com_32_aulas(faltas, nivel, titulo):
    sinal = sinal_de_frequencia("EST", 32, faltas)  # limite: 8 faltas

    if nivel is None:
        assert sinal is None
    else:
        assert (sinal.nivel, sinal.titulo) == (nivel, titulo)


def test_frequencia_sem_aula_registrada_nao_dispara():
    assert sinal_de_frequencia("EST", 0, 0) is None


# ---------- Rotas ----------

HOJE = date.today()
BOA = [("N1", "8.00", "4"), ("N2", "9.00", "6")]


def cenario(faltas_bruno=7):
    return [
        inscricao(1, 1, "Ana Lima", "EST", [("N1", "8.00", "4"), ("N2", "4.00", "6")]),  # queda
        inscricao(2, 2, "Bruno Costa", "EST", BOA, faltas=faltas_bruno),  # frequência
        inscricao(3, 3, "Clara Souza", "EST", BOA),  # sem alerta
        inscricao(4, 1, "Ana Lima", "ALG", BOA, faltas=9),  # frequência alta
    ]


@pytest.fixture
def estado(monkeypatch):
    """Acadêmico simulado (a lista pode ser trocada no teste) e banco SQLite em memória."""
    dados = {"inscricoes": cenario(), "papel": "coordenador"}

    def buscar(*, aluno_id=None, **_):
        return [i for i in dados["inscricoes"] if aluno_id is None or i.aluno.id == aluno_id]

    monkeypatch.setattr(academico, "buscar_inscricoes", buscar)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessoes = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        with sessoes() as db:
            yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[usuario_atual] = lambda: UsuarioAtual(
        id=5, role=dados["papel"], nome="Coordenação"
    )
    dados["cliente"] = TestClient(app)
    yield dados
    app.dependency_overrides.clear()
    engine.dispose()


def alertas_de(cliente, **params):
    return cliente.get("/alertas", params=params).json()["dados"]


def test_lista_os_alertas_do_mais_grave_ao_menos_grave(estado):
    dados = alertas_de(estado["cliente"])

    assert [(a["aluno_nome"], a["tipo"], a["nivel"]) for a in dados["alertas"]] == [
        ("Ana Lima", "queda", "alto"),
        ("Ana Lima", "frequencia", "alto"),
        ("Bruno Costa", "frequencia", "atencao"),
    ]
    assert all(a["estado"] == "pendente" for a in dados["alertas"])
    assert dados["alertas"][0]["ultimo_contato"] == "Sem acompanhamento registrado"


def test_resumo_por_sinal(estado):
    resumo = {r["tipo"]: r for r in alertas_de(estado["cliente"])["resumo"]}

    assert resumo["queda"] == {"tipo": "queda", "total": 1, "graves": 1, "pendentes": 1}
    assert resumo["frequencia"] == {"tipo": "frequencia", "total": 2, "graves": 1, "pendentes": 2}


@pytest.mark.parametrize(
    ("filtro", "quantidade"),
    [({"tipo": "queda"}, 1), ({"nivel": "alto"}, 2), ({"estado": "encerrado"}, 0)],
)
def test_filtros_dos_alertas(estado, filtro, quantidade):
    assert len(alertas_de(estado["cliente"], **filtro)["alertas"]) == quantidade


def test_resumo_nao_muda_com_o_filtro_de_tipo(estado):
    dados = alertas_de(estado["cliente"], tipo="queda")

    assert sum(r["total"] for r in dados["resumo"]) == 3


def test_aluno_inativo_e_inscricao_cancelada_nao_geram_alerta(estado):
    ana = inscricao(1, 1, "Ana Lima", "EST", [("N1", "8.00", "4"), ("N2", "4.00", "6")])
    ana.aluno.status = "inativo"
    cancelada = inscricao(2, 2, "Bruno Costa", "EST", BOA, faltas=9, status="cancelada")
    estado["inscricoes"] = [ana, cancelada]

    assert alertas_de(estado["cliente"])["alertas"] == []


def test_professor_nao_acessa_alertas_nem_acompanhamento(estado):
    estado["papel"] = "professor"
    cliente = estado["cliente"]

    assert cliente.get("/alertas").status_code == 403
    assert cliente.get("/acompanhamentos", params={"aluno_id": 1}).status_code == 403
    assert cliente.put("/alertas/atendimento", json={}).status_code == 403


def atender(cliente, estado_novo, **chave):
    corpo = {"aluno_id": 2, "tipo": "frequencia", "disciplina_id": 1, "estado": estado_novo}
    return cliente.put("/alertas/atendimento", json=corpo | chave)


def test_muda_o_atendimento_do_alerta(estado):
    cliente = estado["cliente"]

    assert atender(cliente, "encerrado").status_code == 200

    alertas = alertas_de(cliente)["alertas"]
    assert alertas[-1]["aluno_nome"] == "Bruno Costa"  # encerrados ficam por último
    assert alertas[-1]["estado"] == "encerrado"
    assert alertas_de(cliente, estado="encerrado")["resumo"][1]["pendentes"] == 1


def test_atendimento_de_alerta_inexistente_e_404(estado):
    resposta = atender(estado["cliente"], "acomp", aluno_id=3)

    assert resposta.status_code == 404


def test_estado_invalido_e_422(estado):
    assert atender(estado["cliente"], "qualquer").status_code == 422


def test_alerta_que_piora_volta_a_pendente(estado):
    cliente = estado["cliente"]
    atender(cliente, "encerrado")

    estado["inscricoes"] = cenario(faltas_bruno=9)  # de "atenção" para "alta"

    bruno = [a for a in alertas_de(cliente)["alertas"] if a["aluno_nome"] == "Bruno Costa"][0]
    assert (bruno["nivel"], bruno["estado"]) == ("alto", "pendente")


def test_alerta_que_continua_igual_mantem_o_atendimento(estado):
    cliente = estado["cliente"]
    atender(cliente, "acomp")

    bruno = [a for a in alertas_de(cliente)["alertas"] if a["aluno_nome"] == "Bruno Costa"][0]
    assert bruno["estado"] == "acomp"


def acompanhar(cliente, **alteracoes):
    corpo = {
        "aluno_id": 1,
        "tipo": "contato",
        "data": HOJE.isoformat(),
        "observacao": "Conversa realizada por telefone.",
    }
    return cliente.post("/acompanhamentos", json=corpo | alteracoes)


def test_registrar_acompanhamento_move_os_alertas_do_aluno(estado):
    cliente = estado["cliente"]

    resposta = acompanhar(cliente, revisao=(HOJE + timedelta(days=7)).isoformat())

    assert resposta.status_code == 201
    registro = resposta.json()["dados"]
    assert registro["responsavel"] == "Coordenação"
    assert registro["revisao_feita"] is False
    por_aluno = {(a["aluno_nome"], a["tipo"]): a for a in alertas_de(cliente)["alertas"]}
    assert por_aluno[("Ana Lima", "queda")]["estado"] == "acomp"
    assert por_aluno[("Ana Lima", "frequencia")]["estado"] == "acomp"
    assert por_aluno[("Bruno Costa", "frequencia")]["estado"] == "pendente"
    assert por_aluno[("Ana Lima", "queda")]["ultimo_contato"].endswith("Contato realizado")


def test_acompanhamento_nao_reabre_alerta_encerrado(estado):
    cliente = estado["cliente"]
    atender(cliente, "encerrado", aluno_id=1, tipo="queda")

    acompanhar(cliente)

    queda = alertas_de(cliente)["alertas"][-1]
    assert (queda["tipo"], queda["estado"]) == ("queda", "encerrado")


def test_lista_acompanhamentos_do_aluno_mais_recentes_primeiro(estado):
    cliente = estado["cliente"]
    acompanhar(cliente, data=(HOJE - timedelta(days=3)).isoformat(), observacao="Primeiro contato")
    acompanhar(cliente, tipo="orientacao", observacao="Orientação sobre a N2")

    lista = cliente.get("/acompanhamentos", params={"aluno_id": 1}).json()["dados"]

    assert [a["observacao"] for a in lista] == ["Orientação sobre a N2", "Primeiro contato"]
    assert cliente.get("/acompanhamentos", params={"aluno_id": 2}).json()["dados"] == []


@pytest.mark.parametrize(
    ("alteracao", "codigo"),
    [
        ({"data": (HOJE + timedelta(days=5)).isoformat()}, "DATA_FUTURA"),
        ({"revisao": (HOJE - timedelta(days=2)).isoformat()}, "REVISAO_ANTERIOR"),
        ({"disciplina_id": 99}, "DISCIPLINA_NAO_INSCRITA"),
    ],
)
def test_acompanhamento_invalido_e_422(estado, alteracao, codigo):
    resposta = acompanhar(estado["cliente"], **alteracao)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == codigo


@pytest.mark.parametrize(
    "alteracao",
    [
        {"observacao": "ab"},
        {"observacao": "x" * 201},
        {"responsavel": "A"},
        {"tipo": "visita"},
        {"data": "ontem"},
        {"campo_extra": 1},
    ],
)
def test_corpo_invalido_do_acompanhamento_e_422(estado, alteracao):
    assert acompanhar(estado["cliente"], **alteracao).status_code == 422


def test_acompanhamento_de_aluno_sem_inscricao_e_404(estado):
    assert acompanhar(estado["cliente"], aluno_id=99).status_code == 404


def test_marcar_revisao_como_feita(estado):
    cliente = estado["cliente"]
    criado = acompanhar(cliente, revisao=HOJE.isoformat()).json()["dados"]

    resposta = cliente.post(f"/acompanhamentos/{criado['id']}/revisao-feita")

    assert resposta.json()["dados"]["revisao_feita"] is True


def test_revisao_feita_sem_revisao_marcada_e_422(estado):
    cliente = estado["cliente"]
    criado = acompanhar(cliente).json()["dados"]

    resposta = cliente.post(f"/acompanhamentos/{criado['id']}/revisao-feita")

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["codigo"] == "SEM_REVISAO"


def test_revisao_vencida_aparece_na_listagem(estado):
    cliente = estado["cliente"]
    acompanhar(
        cliente,
        data=(HOJE - timedelta(days=10)).isoformat(),
        revisao=(HOJE - timedelta(days=2)).isoformat(),
    )

    lista = cliente.get("/acompanhamentos", params={"aluno_id": 1}).json()["dados"]

    assert lista[0]["revisao_vencida"] is True
