"""GET /api/auth/usuarios pelo gateway: a gestão escolhe o professor responsável pelo nome."""

from tests.integration.suporte import Sessao, dados


def test_gestao_lista_professores_pelo_gateway(
    admin: Sessao, coordenacao: Sessao, prof_ana: Sessao
):
    for gestor in (admin, coordenacao):
        lista = dados(gestor.get("/auth/usuarios", params={"role": "professor", "limite": 100}))
        ids = [u["id"] for u in lista]
        assert prof_ana.usuario_id in ids
        assert {u["role"] for u in lista} == {"professor"}
        assert all("email" not in u for u in lista)


def test_professor_nao_lista_usuarios(prof_ana: Sessao, anonimo: Sessao):
    assert prof_ana.get("/auth/usuarios").status_code == 403
    assert anonimo.get("/auth/usuarios").status_code == 401


def test_rota_interna_continua_fechada_no_gateway(admin: Sessao):
    assert admin.get("/auth/internal/usuarios").status_code == 404
