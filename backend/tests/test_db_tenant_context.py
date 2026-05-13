from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from app import db as db_module
from app.db import Database


class _Settings:
    def db_dsn(self) -> str:
        return "postgresql://example"


class _Result:
    def __init__(self, row: dict[str, Any] | None = None) -> None:
        self._row = row

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class _Transaction:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self._events = events

    def __enter__(self) -> _Transaction:
        self._events.append(("transaction_enter", None))
        return self

    def __exit__(self, *args: object) -> None:
        self._events.append(("transaction_exit", None))


class _Connection:
    def __init__(self, events: list[tuple[str, object]]) -> None:
        self._events = events

    def __enter__(self) -> _Connection:
        self._events.append(("connection_enter", None))
        return self

    def __exit__(self, *args: object) -> None:
        self._events.append(("connection_exit", None))

    def transaction(self) -> _Transaction:
        self._events.append(("transaction_requested", None))
        return _Transaction(self._events)

    def execute(self, sql: object, params: tuple[object, ...] = ()) -> _Result:
        sql_text = str(sql)
        self._events.append(("execute", (sql_text, params)))
        if "INSERT INTO properties" in sql_text:
            return _Result(
                {
                    "property_id": UUID("11111111-1111-4111-8111-111111111111"),
                    "tenant_id": "tenant-auth",
                    "name": "Tenant HQ",
                    "address": "Tenant Street",
                    "created_at": None,
                }
            )
        return _Result()


def _install_fake_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []

    def _connect(dsn: str, *, row_factory: object) -> _Connection:
        events.append(("connect", (dsn, row_factory)))
        return _Connection(events)

    monkeypatch.setattr(db_module.psycopg, "connect", _connect)
    return events


def _execute_events(events: list[tuple[str, object]]) -> list[tuple[str, tuple[object, ...]]]:
    return [event[1] for event in events if event[0] == "execute"]  # type: ignore[misc]


def test_tenant_transaction_rejects_missing_or_blank_tenant_before_connect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_fake_connect(monkeypatch)
    database = Database(_Settings())

    for tenant_id in (None, "", "   "):
        with pytest.raises(ValueError, match="Tenant context is required."):
            with database._tenant_transaction(tenant_id):  # type: ignore[arg-type]
                raise AssertionError("tenant transaction should not yield")

    assert events == []


def test_tenant_transaction_sets_transaction_local_context_before_yield(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_fake_connect(monkeypatch)
    database = Database(_Settings())

    with database._tenant_transaction("tenant-auth") as conn:
        conn.execute("SELECT current_setting('app.tenant_id', true)", ())

    execute_events = _execute_events(events)
    assert events[:4] == [
        ("connect", ("postgresql://example", db_module.dict_row)),
        ("connection_enter", None),
        ("transaction_requested", None),
        ("transaction_enter", None),
    ]
    assert "set_config" in execute_events[0][0]
    assert "app.tenant_id" in execute_events[0][0]
    assert execute_events[0][1] == ("tenant-auth",)
    assert "tenant-auth" not in execute_events[0][0]
    assert "current_setting" in execute_events[1][0]


def test_create_property_sets_tenant_context_before_domain_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _install_fake_connect(monkeypatch)
    database = Database(_Settings())

    item = database.create_property(
        tenant_id="tenant-auth",
        actor_user_id="user-auth",
        name="Tenant HQ",
        address="Tenant Street",
    )

    execute_events = _execute_events(events)
    assert item.tenant_id == "tenant-auth"
    assert "set_config" in execute_events[0][0]
    assert execute_events[0][1] == ("tenant-auth",)
    assert "INSERT INTO properties" in execute_events[1][0]
    assert execute_events[1][1] == ("tenant-auth", "Tenant HQ", "Tenant Street")
