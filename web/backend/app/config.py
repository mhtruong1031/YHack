from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    auth0_domain: str
    auth0_audience: str
    gemini_api_key: str
    device_ingest_secret: str
    cors_origins: str = "http://localhost:5173"
    gemini_model: str = "gemini-1.5-flash"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth0_issuer(self) -> str:
        domain = self.auth0_domain.rstrip("/")
        return f"https://{domain}/"


@lru_cache
def get_settings() -> Settings:
    return Settings()
