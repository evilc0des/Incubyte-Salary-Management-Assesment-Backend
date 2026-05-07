from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_postgres_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+"):
        return database_url

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return database_url


class Settings(BaseSettings):
    app_name: str = "FastAPI Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    postgres_user: str = "app_user"
    postgres_password: str = "app_password"
    postgres_db: str = "app_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    integration_database_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return normalize_postgres_database_url(self.database_url)

        return normalize_postgres_database_url(
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

