from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Appointments API"
    database_url: str = "postgresql+psycopg://appointments:appointments-dev-password@localhost:5432/appointments_reference"
    appointments_api_key: str = "dev-appointments-api-key"
    default_page_size: int = 20
    max_page_size: int = 100

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
