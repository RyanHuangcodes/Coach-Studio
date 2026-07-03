from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    cookie_secure: bool = True
    session_cookie_name: str = "session"
    session_ttl_hours: int = 24 * 14


settings = Settings()
