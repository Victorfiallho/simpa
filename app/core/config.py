"""Configuração da aplicação, lida do .env (RNF04: segredos fora do código)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./simpa.db"
    jwt_secret: str
    jwt_expira_minutos: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
