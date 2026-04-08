from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
from alembic import command
from alembic.config import Config
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import UndefinedTable

from app.config import Settings


@dataclass(frozen=True, slots=True)
class _MigrationPaths:
    alembic_ini: Path
    migrations_dir: Path


def run_db_migrations(settings: Settings) -> dict[str, str | None]:
    dsn = settings.db_dsn()
    previous_revision = _current_revision(dsn)
    _upgrade_to_head(sqlalchemy_url=_sqlalchemy_url(dsn), paths=_resolve_migration_paths())
    current_revision = _current_revision(dsn)
    if not current_revision:
        raise RuntimeError("Alembic did not report a current revision after upgrade.")

    return {
        "target_revision": "head",
        "previous_revision": previous_revision,
        "current_revision": current_revision,
    }


def _resolve_migration_paths() -> _MigrationPaths:
    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parents[2],
        current_file.parents[3],
        Path.cwd(),
    ]
    for base_dir in candidates:
        alembic_ini = base_dir / "alembic.ini"
        migrations_dir = base_dir / "migrations"
        if alembic_ini.is_file() and migrations_dir.is_dir():
            return _MigrationPaths(
                alembic_ini=alembic_ini,
                migrations_dir=migrations_dir,
            )

    raise FileNotFoundError("Alembic assets not found. Expected alembic.ini and migrations/.")


def _sqlalchemy_url(dsn: str) -> str:
    conninfo = conninfo_to_dict(dsn)
    user = quote_plus(str(conninfo["user"]))
    password = quote_plus(str(conninfo["password"]))
    host = str(conninfo["host"])
    port = str(conninfo["port"])
    dbname = quote_plus(str(conninfo["dbname"]))
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"


def _current_revision(dsn: str) -> str | None:
    try:
        with psycopg.connect(dsn) as conn:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
    except UndefinedTable:
        return None

    if not row:
        return None
    return str(row[0])


def _upgrade_to_head(*, sqlalchemy_url: str, paths: _MigrationPaths) -> None:
    config = Config(str(paths.alembic_ini))
    config.set_main_option("script_location", str(paths.migrations_dir))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)
    command.upgrade(config, "head")
