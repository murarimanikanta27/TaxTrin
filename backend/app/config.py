"""Application configuration, loaded from environment variables / .env file.

Nothing tax-rate related lives here -- statutory constants belong in the
database-backed TaxYearConfig table (see app.models.tax_config) so they can be
edited by a system_admin without a code deploy, per the "dynamic tax engine"
requirement.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TaxTrin API"
    environment: str = "development"

    # Defaults to a local SQLite file so the POC runs with zero external setup.
    # Point this at a PostgreSQL DSN (e.g. postgresql+psycopg://user:pass@host/db)
    # for a production-shaped deployment.
    database_url: str = "sqlite:///./taxtrin.db"

    jwt_secret: str = "poc-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    storage_dir: str = "storage"

    # Path to the Tesseract OCR binary (used by app.services.ocr for TD4
    # drag-and-drop parsing). Only needed on Windows, where pytesseract can't
    # find tesseract.exe on PATH automatically. Leave blank on Linux/macOS
    # where `tesseract` is normally already on PATH after an apt/brew install.
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
