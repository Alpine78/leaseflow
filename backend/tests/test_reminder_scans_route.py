from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import date

import pytest


def _reminder_scans_module():
    return importlib.import_module("app.routes.reminder_scans")


@dataclass(slots=True)
class _ScanResult:
    tenant_id: str
    as_of_date: date
    days: int
    candidate_count: int
    created_count: int
    duplicate_count: int


class _FakeDb:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_due_lease_reminder_notifications(
        self,
        tenant_id: str,
        as_of_date: date,
        days: int,
    ) -> _ScanResult:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "as_of_date": as_of_date,
                "days": days,
            }
        )
        return _ScanResult(
            tenant_id=tenant_id,
            as_of_date=as_of_date,
            days=days,
            candidate_count=2,
            created_count=1,
            duplicate_count=1,
        )


def test_scan_due_lease_reminders_uses_detail_and_defaults(monkeypatch) -> None:
    reminder_scans = _reminder_scans_module()
    db = _FakeDb()
    monkeypatch.setattr(reminder_scans, "_today", lambda: date(2026, 4, 7))
    event = {
        "source": "leaseflow.internal",
        "detail-type": "scan_due_lease_reminders",
        "detail": {"tenant_id": "tenant-auth"},
    }

    payload = reminder_scans.scan_due_lease_reminders(event, db)

    assert db.calls == [
        {
            "tenant_id": "tenant-auth",
            "as_of_date": date(2026, 4, 7),
            "days": 7,
        }
    ]
    assert payload == {
        "tenant_id": "tenant-auth",
        "as_of_date": "2026-04-07",
        "days": 7,
        "candidate_count": 2,
        "created_count": 1,
        "duplicate_count": 1,
    }


def test_scan_due_lease_reminders_supports_explicit_detail_values() -> None:
    reminder_scans = _reminder_scans_module()
    db = _FakeDb()
    event = {
        "source": "leaseflow.internal",
        "detail-type": "scan_due_lease_reminders",
        "detail": {
            "tenant_id": "tenant-auth",
            "days": 14,
            "as_of_date": "2026-04-09",
        },
    }

    reminder_scans.scan_due_lease_reminders(event, db)

    assert db.calls == [
        {
            "tenant_id": "tenant-auth",
            "as_of_date": date(2026, 4, 9),
            "days": 14,
        }
    ]


def test_scan_due_lease_reminders_requires_tenant_id() -> None:
    reminder_scans = _reminder_scans_module()
    db = _FakeDb()

    with pytest.raises(ValueError, match="Detail field 'tenant_id' is required."):
        reminder_scans.scan_due_lease_reminders(
            {
                "source": "leaseflow.internal",
                "detail-type": "scan_due_lease_reminders",
                "detail": {},
            },
            db,
        )

    assert db.calls == []


def test_scan_due_lease_reminders_rejects_invalid_days() -> None:
    reminder_scans = _reminder_scans_module()
    db = _FakeDb()

    with pytest.raises(
        ValueError,
        match="Detail field 'days' must be an integer between 1 and 31.",
    ):
        reminder_scans.scan_due_lease_reminders(
            {
                "source": "leaseflow.internal",
                "detail-type": "scan_due_lease_reminders",
                "detail": {"tenant_id": "tenant-auth", "days": 0},
            },
            db,
        )

    assert db.calls == []


def test_scan_due_lease_reminders_rejects_invalid_as_of_date() -> None:
    reminder_scans = _reminder_scans_module()
    db = _FakeDb()

    with pytest.raises(ValueError, match="Detail field 'as_of_date' must use YYYY-MM-DD."):
        reminder_scans.scan_due_lease_reminders(
            {
                "source": "leaseflow.internal",
                "detail-type": "scan_due_lease_reminders",
                "detail": {
                    "tenant_id": "tenant-auth",
                    "as_of_date": "04/09/2026",
                },
            },
            db,
        )

    assert db.calls == []
