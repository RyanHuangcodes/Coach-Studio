from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
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
