import os
import platform
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from forkflux_api.constants import CLIScopeEnum


def _global_sqlite_db_path() -> Path:
    system = platform.system().lower()
    app_name = "forkflux"

    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name / "forkflux.db"

    if system == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / app_name / "forkflux.db"
        return Path.home() / "AppData" / "Roaming" / app_name / "forkflux.db"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / app_name / "forkflux.db"

    return Path.home() / ".local" / "share" / app_name / "forkflux.db"


def _local_sqlite_db_path() -> Path:
    return Path.cwd() / ".forkflux" / "forkflux.db"


def _build_default_database_url(db_scope: CLIScopeEnum | None) -> str:
    local_path = _local_sqlite_db_path()
    global_path = _global_sqlite_db_path()

    if db_scope is not None:
        # Explicit scope: select the corresponding path unconditionally.
        sqlite_path = global_path if db_scope == CLIScopeEnum.user else local_path
    elif local_path.exists():
        sqlite_path = local_path
    elif global_path.exists():
        sqlite_path = global_path
    else:
        sqlite_path = local_path

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{sqlite_path}"


class Settings(BaseSettings):
    db_scope: CLIScopeEnum | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_nested_max_split=1, env_nested_delimiter="_"
    )

    database_url: str = Field(default="")

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = _build_default_database_url(self.db_scope)
        else:
            scheme = urlsplit(self.database_url).scheme
            if scheme == "sqlite+aiosqlite":
                return self

            if scheme.startswith("postgresql"):
                PostgresDsn(self.database_url)
                return self

            raise ValueError("Unsupported database URL scheme. Use sqlite+aiosqlite or postgresql(+driver).")
        return self


@lru_cache()
def get_settings(db_scope: CLIScopeEnum | None = None) -> Settings:
    if db_scope is None:
        return Settings()
    return Settings(db_scope=db_scope)
