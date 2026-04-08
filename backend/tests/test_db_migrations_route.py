from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace


def _db_migrations_module():
    return importlib.import_module("app.routes.db_migrations")


def test_run_db_migrations_returns_previous_and_current_revision(monkeypatch) -> None:
    db_migrations = _db_migrations_module()
    upgrade_calls: list[dict[str, object]] = []
    revisions = iter(["20260310_0001", "20260407_0005"])
    paths = SimpleNamespace(
        alembic_ini=Path("/var/task/alembic.ini"),
        migrations_dir=Path("/var/task/migrations"),
    )

    monkeypatch.setattr(db_migrations, "_resolve_migration_paths", lambda: paths)
    monkeypatch.setattr(
        db_migrations,
        "_sqlalchemy_url",
        lambda settings: "postgresql+psycopg://leaseflow_admin:secret@db:5432/leaseflow",
    )
    monkeypatch.setattr(db_migrations, "_current_revision", lambda dsn: next(revisions))

    def _fake_upgrade(*, sqlalchemy_url: str, paths: object) -> None:
        upgrade_calls.append({"sqlalchemy_url": sqlalchemy_url, "paths": paths})

    monkeypatch.setattr(db_migrations, "_upgrade_to_head", _fake_upgrade)

    payload = db_migrations.run_db_migrations(
        SimpleNamespace(db_dsn=lambda: "host=db port=5432 dbname=leaseflow user=leaseflow_admin")
    )

    assert payload == {
        "target_revision": "head",
        "previous_revision": "20260310_0001",
        "current_revision": "20260407_0005",
    }
    assert upgrade_calls == [
        {
            "sqlalchemy_url": "postgresql+psycopg://leaseflow_admin:secret@db:5432/leaseflow",
            "paths": paths,
        }
    ]


def test_run_db_migrations_reports_null_previous_revision_when_version_table_missing(
    monkeypatch,
) -> None:
    db_migrations = _db_migrations_module()
    revisions = iter([None, "20260407_0005"])

    monkeypatch.setattr(
        db_migrations,
        "_resolve_migration_paths",
        lambda: SimpleNamespace(
            alembic_ini=Path("/var/task/alembic.ini"),
            migrations_dir=Path("/var/task/migrations"),
        ),
    )
    monkeypatch.setattr(
        db_migrations,
        "_sqlalchemy_url",
        lambda settings: "postgresql+psycopg://leaseflow_admin:secret@db:5432/leaseflow",
    )
    monkeypatch.setattr(db_migrations, "_current_revision", lambda dsn: next(revisions))
    monkeypatch.setattr(db_migrations, "_upgrade_to_head", lambda **kwargs: None)

    payload = db_migrations.run_db_migrations(
        SimpleNamespace(db_dsn=lambda: "host=db port=5432 dbname=leaseflow user=leaseflow_admin")
    )

    assert payload == {
        "target_revision": "head",
        "previous_revision": None,
        "current_revision": "20260407_0005",
    }
