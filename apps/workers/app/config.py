from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Same secret the api uses to encrypt provider tokens; shared env var.
    api_secret_key: str = "change-me-in-production"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "aiworkspace"
    postgres_password: str = "aiworkspace"
    postgres_db: str = "aiworkspace"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "aiworkspace"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"

    repo_storage_path: str = "/data/repositories"


settings = Settings()
