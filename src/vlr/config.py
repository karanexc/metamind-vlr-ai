"""Application settings, loaded from environment variables and .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://vlr:vlr_dev_password@localhost:5433/vlr"

    vlr_base_url: str = "https://www.vlr.gg"
    scrape_delay_seconds: float = 2.0
    scrape_user_agent: str = (
        "vlr-analytics-dissertation/0.1 "
        "(Masters research project; replace with your contact email)"
    )
    scrape_timeout_seconds: int = 20


settings = Settings()
