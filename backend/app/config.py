from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        # Managed hosts (Render/Heroku/etc.) often hand out a "postgres://" URL,
        # which SQLAlchemy 2.0 no longer accepts. Pin the driver to psycopg2 too:
        # newer SQLAlchemy defaults bare "postgresql://" to psycopg (v3), which
        # isn't installed.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix):]
        return value
    secret_key: str
    cookie_secure: bool = True
    session_cookie_name: str = "session"
    session_ttl_hours: int = 24 * 14
    anthropic_api_key: str = ""
    # Web Push (VAPID). Empty = push disabled (the app still works without it).
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:example@example.com"


settings = Settings()
