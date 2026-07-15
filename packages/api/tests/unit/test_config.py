from pathlib import Path
from unittest.mock import patch

import pytest
from forkflux_api.config import _build_default_database_url
from forkflux_api.constants import CLIScopeEnum


@pytest.fixture
def db_paths(tmp_path: Path):
    """Patch the path helpers to return predictable paths under tmp_path."""
    local_path = tmp_path / "local" / "forkflux.db"
    global_path = tmp_path / "global" / "forkflux.db"

    with (
        patch("forkflux_api.config._local_sqlite_db_path", return_value=local_path),
        patch("forkflux_api.config._global_sqlite_db_path", return_value=global_path),
    ):
        yield local_path, global_path


# --- Explicit scope: unconditional path selection ---


def test_build_default_database_url_user_scope_always_global(db_paths: tuple[Path, Path]) -> None:
    """CLIScopeEnum.user must resolve to the global path even when neither path exists."""
    local_path, global_path = db_paths

    url = _build_default_database_url(CLIScopeEnum.user)

    assert url == f"sqlite+aiosqlite:///{global_path}"
    assert str(local_path) not in url


def test_build_default_database_url_local_scope_always_local(db_paths: tuple[Path, Path]) -> None:
    """CLIScopeEnum.local must resolve to the local path even when neither path exists."""
    local_path, global_path = db_paths

    url = _build_default_database_url(CLIScopeEnum.local)

    assert url == f"sqlite+aiosqlite:///{local_path}"
    assert str(global_path) not in url


def test_build_default_database_url_project_scope_always_local(db_paths: tuple[Path, Path]) -> None:
    """CLIScopeEnum.project must resolve to the local path even when neither path exists."""
    local_path, global_path = db_paths

    url = _build_default_database_url(CLIScopeEnum.project)

    assert url == f"sqlite+aiosqlite:///{local_path}"
    assert str(global_path) not in url


def test_build_default_database_url_user_scope_ignores_existing_local(db_paths: tuple[Path, Path]) -> None:
    """CLIScopeEnum.user must resolve to global even if a local db already exists."""
    local_path, global_path = db_paths
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.touch()

    url = _build_default_database_url(CLIScopeEnum.user)

    assert url == f"sqlite+aiosqlite:///{global_path}"


# --- Fallback: db_scope is None ---


def test_build_default_database_url_none_scope_prefers_existing_local(db_paths: tuple[Path, Path]) -> None:
    """When db_scope is None and local_path exists, select local_path."""
    local_path, _ = db_paths
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.touch()

    url = _build_default_database_url(None)

    assert url == f"sqlite+aiosqlite:///{local_path}"


def test_build_default_database_url_none_scope_uses_global_when_only_global_exists(
    db_paths: tuple[Path, Path],
) -> None:
    """When db_scope is None, local_path missing, but global_path exists, select global_path."""
    _, global_path = db_paths
    global_path.parent.mkdir(parents=True, exist_ok=True)
    global_path.touch()

    url = _build_default_database_url(None)

    assert url == f"sqlite+aiosqlite:///{global_path}"


def test_build_default_database_url_none_scope_defaults_to_local_when_neither_exists(
    db_paths: tuple[Path, Path],
) -> None:
    """When db_scope is None and neither path exists, default to local_path."""
    local_path, _ = db_paths

    url = _build_default_database_url(None)

    assert url == f"sqlite+aiosqlite:///{local_path}"
