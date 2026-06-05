from functools import lru_cache

from pydantic import PostgresDsn, field_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_max_split=1, env_nested_delimiter="_"
    )

    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | MultiHostUrl) -> str:
        if isinstance(value, MultiHostUrl):
            return value.__str__()

        PostgresDsn(value)
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
