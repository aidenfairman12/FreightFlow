from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://planelogistics:changeme@postgres:5432/planelogistics"
    redis_url: str = "redis://redis:6379"
    frontend_url: str = "http://localhost:3000"
    # EIA API key for diesel/crude prices (free at eia.gov)
    eia_api_key: str = ""
    # FRED API key for freight TSI (free at https://fred.stlouisfed.org/docs/api/api_key.html)
    fred_api_key: str = ""
    # FAF5 data directory (relative to backend/)
    faf5_data_dir: str = "data/faf5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
