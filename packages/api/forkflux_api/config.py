import os
import platform
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, field_validator
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir(app_name: str) -> Path:
    system = platform.system().lower()

    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    if system == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / app_name
        return Path.home() / "AppData" / "Roaming" / app_name

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / app_name

    return Path.home() / ".local" / "share" / app_name


def _default_sqlite_db_path() -> Path:
    return _default_data_dir("forkflux") / "forkflux.db"


def _build_default_database_url() -> str:
    sqlite_path = _default_sqlite_db_path()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{sqlite_path}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_max_split=1, env_nested_delimiter="_"
    )

    database_url: str = Field(default_factory=_build_default_database_url)

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | MultiHostUrl) -> str:
        if isinstance(value, MultiHostUrl):
            return value.__str__()

        scheme = urlsplit(value).scheme
        if scheme in {"sqlite", "sqlite+aiosqlite"}:
            return value

        if scheme.startswith("postgresql"):
            PostgresDsn(value)
            return value

        raise ValueError("Unsupported database URL scheme. Use sqlite(+aiosqlite) or postgresql(+driver).")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
