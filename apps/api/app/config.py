from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "change-me-in-production"
    api_debug: bool = False

    postgres_user: str = "aiworkspace"
    postgres_password: str = "aiworkspace"
    postgres_db: str = "aiworkspace"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "aiworkspace"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    github_webhook_secret: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    repo_storage_path: str = "/data/repositories"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    cors_origins: list[str] = ["http://localhost:3001", "http://127.0.0.1:3001"]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
