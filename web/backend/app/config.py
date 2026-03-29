from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_surrounding_quotes(raw: str) -> str:
    o = raw.strip()
    if len(o) >= 2 and o[0] == o[-1] and o[0] in "\"'":
        return o[1:-1].strip()
    return o


def _normalize_browser_origin(raw: str) -> str:
    """Match browser `Origin` (no path; strip quotes/spaces from env; no trailing slash)."""
    o = _strip_surrounding_quotes(raw).rstrip("/")
    return o


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
    cors_origins: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("CORS_ORIGINS", "CORS_ORIGIN"),
    )
    cors_origin_regex: str = Field(
        default="",
        description="Full-match regex for extra allowed Origin values (e.g. Vercel preview URLs).",
    )
    # google-generativeai: 1.5 IDs often 404 on current v1beta; use a current stable id.
    gemini_model: str = "gemini-2.5-flash"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _cors_origins_empty_falls_back(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "http://localhost:5173"
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        out: list[str] = []
        for part in self.cors_origins.split(","):
            o = _normalize_browser_origin(part)
            if o:
                out.append(o)
        return out

    @property
    def cors_origin_regex_pattern(self) -> str | None:
        r = _strip_surrounding_quotes(self.cors_origin_regex)
        return r or None

    @property
    def auth0_issuer(self) -> str:
        domain = self.auth0_domain.rstrip("/")
        return f"https://{domain}/"


@lru_cache
def get_settings() -> Settings:
    return Settings()
