from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    database_url: str = "postgresql+asyncpg://planelogistics:changeme@postgres:5432/planelogistics"
    redis_url: str = "redis://redis:6379"
    frontend_url: str = "http://localhost:3000"
    poll_interval_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
