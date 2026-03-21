from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    database_url: str = "postgresql+asyncpg://planelogistics:changeme@postgres:5432/planelogistics"
    redis_url: str = "redis://redis:6379"
    frontend_url: str = "http://localhost:3000"
    poll_interval_seconds: int = 30
    # Phase 6: EIA API key for fuel prices (free at eia.gov)
    eia_api_key: str = ""
    # Optional: AirLabs API key for bulk SWISS route data (free at airlabs.co)
    airlabs_api_key: str = ""
    # Collect mode: minimal resources, data collection only (no UI, no heavy compute)
    collect_mode: bool = False
    # OpenSky daily credit limit (free tier = 4000)
    opensky_daily_credit_limit: int = 4000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
