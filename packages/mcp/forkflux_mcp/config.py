from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_max_split=1, env_nested_delimiter="_"
    )

    forkflux_api_url: str = "http://localhost:8000/api/v1"
    forkflux_api_key: str | None = None
    forkflux_shared_api_key: str | None = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()
