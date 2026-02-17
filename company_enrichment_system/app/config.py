from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'company_enrichment_system'
    app_version: str = '1.0.0'

    batch_size: int = Field(default=100, ge=50, le=100)
    max_retries: int = 3
    request_timeout_seconds: float = 8.0
    rate_limit_per_second: int = 10
    max_concurrency: int = 20

    # Optional generic official search provider
    search_api_url: str | None = None
    search_api_key: str | None = None

    # Optional SerpApi (official API) provider for website fallback
    serpapi_url: str = 'https://serpapi.com/search.json'
    serpapi_api_key: str | None = None

    google_places_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
