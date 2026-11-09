from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bolna Knowledge Gap Miner"
    app_version: str = "0.1.0"
    environment: str = "development"

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/knowledge_gap_miner"
    )

    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
