from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
from uuid import UUID

from app.db import Database
from app.models import NotificationContactSuppression


def test_notification_contact_suppression_model_carries_safe_domain_fields() -> None:
    suppression = NotificationContactSuppression(
        suppression_id=UUID("11111111-1111-4111-8111-111111111111"),
        tenant_id="tenant-auth",
        contact_id=UUID("22222222-2222-4222-8222-222222222222"),
        reason="bounce",
        created_at=datetime(2026, 5, 12, tzinfo=UTC),
    )

    assert suppression.reason == "bounce"
    assert suppression.contact_id == UUID("22222222-2222-4222-8222-222222222222")


def test_database_exposes_notification_contact_suppression_methods() -> None:
    create_params = signature(Database.create_notification_contact_suppression).parameters
    list_params = signature(Database.list_notification_contact_suppressions).parameters

    assert list(create_params) == [
        "self",
        "tenant_id",
        "actor_user_id",
        "contact_id",
        "reason",
        "audit_source",
    ]
    assert create_params["audit_source"].default == "leaseflow.internal"
    assert list(list_params) == ["self", "tenant_id", "contact_id"]
    assert list_params["contact_id"].default is None
