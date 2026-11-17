"""Configurações centrais da aplicação via Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente e arquivo .env."""

    app_name: str = "Calculadora RTC RFB Free Suite PY"
    app_env: str = "development"
    app_version: str = "0.1.0"
    debug: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    serve_frontend: bool = True
    reference_db_path: str = ""

    cors_origins: str = Field(
        default="http://localhost:8080,http://localhost:8000,http://127.0.0.1:8080,http://127.0.0.1:8000"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna a lista normalizada de origens permitidas no CORS."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def frontend_dir(self) -> Path:
        """Caminho absoluto para o diretório frontend no monorepo."""
        return Path(__file__).resolve().parents[3] / "frontend"

    @property
    def resolved_reference_db_path(self) -> Path:
        """Caminho absoluto para o banco SQLite de tabelas oficiais da RFB."""
        if self.reference_db_path:
            return Path(self.reference_db_path)
        return Path(__file__).resolve().parents[2] / "data" / "rtc_referencias.db"


@lru_cache
def get_settings() -> Settings:
    """Instância cacheada das configurações da aplicação."""
    return Settings()

