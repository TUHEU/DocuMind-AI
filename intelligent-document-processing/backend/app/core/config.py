from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Application settings, read from environment variables or a local backend/.env file.

    Secrets (database password, JWT secret, SMTP key) are NEVER written here:
    put the real values only in backend/.env, which git ignores.
    """

    app_name: str = "Intelligent Document Processing API"
    app_version: str = "0.4.0"
    environment: str = "development"

    # MySQL connection
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "idp_user"
    db_password: str = "change_me"
    db_name: str = "idp_db"

    # Browser origins allowed to call the API (Vite 5173, Create React App 3000)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Protected storage directory for uploaded documents (Phase 5)
    storage_dir: str = "./data/storage"

    # --- Authentication (Phase 4) ---
    jwt_secret: str = "dev-only-change-me-please-use-a-long-random-string"
    jwt_expire_seconds: int = 1800          # 30 minutes (provisional, see contract)
    max_failed_logins: int = 5              # lock the account after this many wrong passwords
    lockout_minutes: int = 15
    password_min_length: int = 8
    password_scrypt_n: int = 2**14          # lower only in tests

    # --- E-mail (Brevo SMTP). Leave email_backend=console until you have set the key in .env ---
    email_backend: str = "console"          # console | smtp
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_login: str = ""                    # your Brevo SMTP login (put it in .env)
    smtp_key: str = ""                      # your Brevo SMTP key (put it in .env, never in code)
    email_from: str = ""                    # a sender address verified in Brevo
    email_from_name: str = "DocuMind AI"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_url(self) -> URL:
        """Preferred form for SQLAlchemy: no manual escaping of the password needed."""
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def database_url(self) -> str:
        """Escaped string form (used by tools that need a string)."""
        return self.sqlalchemy_url.render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
