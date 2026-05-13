"""Runtime config from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_maps_key: str | None = None
    solver_seconds: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    sample_data_dir: str = "../sample_data"

    # Cosmos DB (optional — backend works without it for local dev)
    cosmos_endpoint: str | None = None
    cosmos_database: str = "routing"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
