"""Teste mínimo: garante que o pytest coleta algo e que o pacote importa."""

from app.core.config import Settings


def test_settings_carrega_valores_padrao(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "segredo-de-teste")
    settings = Settings(_env_file=None)

    assert settings.jwt_secret == "segredo-de-teste"
    assert settings.jwt_expira_minutos == 60
    assert settings.database_url.startswith("sqlite")
