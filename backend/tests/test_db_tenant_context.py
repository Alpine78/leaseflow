from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import pytest

from app import db as db_module
from app.db import Database
from app.models import (
    NotificationEmailDelivery,
    NotificationEmailDeliveryPreparationResult,
    ReminderScanResult,
)


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


class _RlsSafeJobDatabase(Database):
    def __init__(self) -> None:
        super().__init__(_Settings())
        self.calls: list[tuple[str, object]] = []

    def list_due_lease_reminder_tenants(self, *, as_of_date: date, days: int) -> list[str]:
        self.calls.append(("discover_reminder_tenants", (as_of_date, days)))
        return ["tenant-a", "tenant-b"]

    def _create_due_lease_reminder_notifications_for_tenant(
        self,
        *,
        tenant_id: str,
        as_of_date: date,
        days: int,
    ) -> ReminderScanResult:
        self.calls.append(("scan_tenant", tenant_id))
        created_count = 2 if tenant_id == "tenant-a" else 1
        return ReminderScanResult(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=days,
            tenant_count=1,
            candidate_count=created_count + 1,
            created_count=created_count,
            duplicate_count=1,
        )

    def list_notification_email_delivery_tenants(
        self,
        *,
        max_attempts: int | None = None,
    ) -> list[str]:
        self.calls.append(("discover_delivery_tenants", max_attempts))
        return ["tenant-a", "tenant-b"]

    def _create_missing_notification_email_deliveries_for_tenant(
        self,
        *,
        tenant_id: str,
    ) -> NotificationEmailDeliveryPreparationResult:
        self.calls.append(("prepare_tenant", tenant_id))
        created_count = 2 if tenant_id == "tenant-a" else 1
        return NotificationEmailDeliveryPreparationResult(
            tenant_id=tenant_id,
            candidate_count=created_count,
            created_count=created_count,
            duplicate_count=0,
            suppressed_contact_count=1,
        )

    def _list_pending_notification_email_deliveries_for_tenant(
        self,
        *,
        tenant_id: str,
        max_attempts: int,
        limit: int,
    ) -> list[NotificationEmailDelivery]:
        self.calls.append(("list_pending_tenant", (tenant_id, max_attempts, limit)))
        if tenant_id == "tenant-a":
            return [_delivery("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", tenant_id, 2)]
        return [_delivery("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", tenant_id, 1)]


def _delivery(delivery_id: str, tenant_id: str, day: int) -> NotificationEmailDelivery:
    return NotificationEmailDelivery(
        delivery_id=UUID(delivery_id),
        tenant_id=tenant_id,
        notification_id=UUID("11111111-1111-4111-8111-111111111111"),
        contact_id=UUID("22222222-2222-4222-8222-222222222222"),
        event_correlation_token=UUID("33333333-3333-4333-8333-333333333333"),
        recipient_email="recipient@example.test",
        subject="Rent due soon",
        body="Rent is due soon.",
        due_date=date(2026, 5, day),
        status="pending",
        attempt_count=0,
        last_attempt_at=None,
        sent_at=None,
        last_error_code=None,
        created_at=datetime(2026, 5, day, tzinfo=UTC),
        updated_at=datetime(2026, 5, day, tzinfo=UTC),
    )


def test_unscoped_reminder_scan_discovers_and_processes_tenants_one_by_one() -> None:
    database = _RlsSafeJobDatabase()

    result = database.create_due_lease_reminder_notifications(
        tenant_id=None,
        as_of_date=date(2026, 5, 13),
        days=7,
    )

    assert database.calls == [
        ("discover_reminder_tenants", (date(2026, 5, 13), 7)),
        ("scan_tenant", "tenant-a"),
        ("scan_tenant", "tenant-b"),
    ]
    assert result.tenant_id is None
    assert result.tenant_count == 2
    assert result.candidate_count == 5
    assert result.created_count == 3
    assert result.duplicate_count == 2


def test_explicit_reminder_scan_does_not_discover_tenants() -> None:
    database = _RlsSafeJobDatabase()

    result = database.create_due_lease_reminder_notifications(
        tenant_id="tenant-a",
        as_of_date=date(2026, 5, 13),
        days=7,
    )

    assert database.calls == [("scan_tenant", "tenant-a")]
    assert result.tenant_id == "tenant-a"
    assert result.tenant_count == 1


def test_unscoped_delivery_preparation_discovers_and_processes_tenants_one_by_one() -> None:
    database = _RlsSafeJobDatabase()

    result = database.create_missing_notification_email_deliveries(tenant_id=None)

    assert database.calls == [
        ("discover_delivery_tenants", None),
        ("prepare_tenant", "tenant-a"),
        ("prepare_tenant", "tenant-b"),
    ]
    assert result.tenant_id is None
    assert result.candidate_count == 3
    assert result.created_count == 3
    assert result.duplicate_count == 0
    assert result.suppressed_contact_count == 2


def test_unscoped_pending_delivery_discovers_tenants_and_applies_global_limit() -> None:
    database = _RlsSafeJobDatabase()

    pending = database.list_pending_notification_email_deliveries(
        tenant_id=None,
        max_attempts=3,
        limit=1,
    )

    assert database.calls == [
        ("discover_delivery_tenants", 3),
        ("list_pending_tenant", ("tenant-a", 3, 1)),
        ("list_pending_tenant", ("tenant-b", 3, 1)),
    ]
    assert [item.tenant_id for item in pending] == ["tenant-b"]


def test_explicit_pending_delivery_does_not_discover_tenants() -> None:
    database = _RlsSafeJobDatabase()

    pending = database.list_pending_notification_email_deliveries(
        tenant_id="tenant-a",
        max_attempts=3,
        limit=10,
    )

    assert database.calls == [("list_pending_tenant", ("tenant-a", 3, 10))]
    assert [item.tenant_id for item in pending] == ["tenant-a"]
