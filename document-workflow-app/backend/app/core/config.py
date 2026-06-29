from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Document Workflow API"
    environment: str = "local"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "docflow_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    database_url: str | None = None

    file_storage_provider: str = "local"
    local_storage_path: str = "storage/uploads"
    max_upload_size_mb: int = 25
    allowed_file_extensions: str = ".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt,.zip"

    one_c_base_url: str = "http://1c-server/base/hs/docflow"
    one_c_username: str = ""
    one_c_password: str = ""
    one_c_timeout_seconds: int = 30
    one_c_enabled: bool = False
    one_c_payment_request_endpoint: str = "/payment-requests"
    one_c_health_endpoint: str = "/health"
    one_c_connection_test_endpoint: str = "/health"
    one_c_verify_ssl: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "local", "true", "1", "yes", "on"}:
                return True
        return value

    @staticmethod
    def _normalize_postgres_driver(url: str) -> str:
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self._normalize_postgres_driver(self.database_url)
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def allowed_file_extension_set(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.allowed_file_extensions.split(",")
            if item.strip()
        }


settings = Settings()
