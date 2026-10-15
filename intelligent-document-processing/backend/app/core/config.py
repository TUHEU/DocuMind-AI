from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a local .env file."""

    app_name: str = "Intelligent Document Processing API"
    app_version: str = "0.1.0"
    environment: str = "development"

    # MySQL connection (used from Phase 2 onward)
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "idp_user"
    db_password: str = "change_me"
    db_name: str = "idp_db"

    # Protected storage directory for uploaded documents (Phase 3)
    storage_dir: str = "./data/storage"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
