from functools import lru_cache
from urllib.parse import quote_plus

from sqlalchemy.engine import URL

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

    # Browser origins allowed to call the API (React dev servers: Vite 5173, Create React App 3000)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Protected storage directory for uploaded documents (Phase 3)
    storage_dir: str = "./data/storage"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        """URL string with the user and password safely escaped (passwords may contain @, :, / ...)."""
        return (
            f"mysql+pymysql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sqlalchemy_url(self) -> URL:
        """Preferred form for SQLAlchemy: no manual escaping needed."""
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
