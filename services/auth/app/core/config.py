"""Configuração do serviço auth, lida das variáveis de ambiente (RNF04: segredos fora do código)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # No Docker vem do docker-compose.yml; o padrão só serve para rodar os testes localmente.
    database_url: str = "sqlite:///./dev.db"
    # Prefixo que o gateway usa para este serviço (faz o Swagger funcionar atrás do nginx).
    root_path: str = ""

    # Pasta do par de chaves RSA que assina os tokens (volume Docker, nunca no Git).
    chaves_dir: str = "chaves"
    jwt_expira_minutos: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
