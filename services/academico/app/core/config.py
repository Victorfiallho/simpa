"""Configuração do serviço acadêmico, lida das variáveis de ambiente (RNF04)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # No Docker vem do docker-compose.yml; o padrão só serve para rodar os testes localmente.
    database_url: str = "sqlite:///./dev.db"
    # Prefixo que o gateway usa para este serviço (faz o Swagger funcionar atrás do nginx).
    root_path: str = ""

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    auth_jwks_url: str = "http://auth:8000/.well-known/jwks.json"
    # API interna do auth, usada para conferir o professor de uma disciplina.
    auth_url: str = "http://auth:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
