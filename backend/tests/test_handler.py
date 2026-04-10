import json
from types import SimpleNamespace

from app import handler


def test_health_endpoint() -> None:
    event = {
        "rawPath": "/health",
        "requestContext": {"http": {"method": "GET"}},
    }
    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"


def test_health_endpoint_accepts_stage_prefixed_raw_path() -> None:
    event = {
        "rawPath": "/dev/health",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "GET"},
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "ok"


def test_list_properties_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(handler, "list_properties", lambda event, db: {"items": []})

    event = {
        "rawPath": "/dev/properties",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"items": []}


def test_list_leases_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(handler, "list_leases", lambda event, db: {"items": []}, raising=False)

    event = {
        "rawPath": "/dev/leases",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"items": []}


def test_create_lease_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "create_lease",
        lambda event, db, body: {"lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
        raising=False,
    )

    event = {
        "rawPath": "/dev/leases",
        "body": json.dumps(
            {
                "property_id": "11111111-1111-1111-1111-111111111111",
                "resident_name": "Alice Example",
                "start_date": "2026-05-01",
                "end_date": "2027-04-30",
            }
        ),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "POST"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 201
    assert json.loads(response["body"]) == {"lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}


def test_list_due_lease_reminders_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "list_due_lease_reminders",
        lambda event, db: {"items": []},
        raising=False,
    )

    event = {
        "rawPath": "/dev/lease-reminders/due-soon",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"items": []}


def test_list_notifications_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "list_notifications",
        lambda event, db: {"items": []},
        raising=False,
    )

    event = {
        "rawPath": "/dev/notifications",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"items": []}


def test_mark_notification_read_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "mark_notification_read",
        lambda event, db, notification_id: {
            "notification_id": str(notification_id),
            "read_at": "2026-04-09T10:00:00+00:00",
        },
        raising=False,
    )

    event = {
        "rawPath": "/dev/notifications/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/read",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "notification_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "read_at": "2026-04-09T10:00:00+00:00",
    }


def test_mark_notification_read_rejects_invalid_notification_uuid(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )

    event = {
        "rawPath": "/dev/notifications/not-a-uuid/read",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "Invalid notification ID."}


def test_update_property_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "update_property",
        lambda event, db, property_id: {
            "property_id": str(property_id),
            "tenant_id": "tenant-123",
            "name": "Updated HQ",
            "address": "Updated Street 1",
            "created_at": "2026-03-12T00:00:00+00:00",
        },
        raising=False,
    )

    event = {
        "rawPath": "/dev/properties/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "body": json.dumps({"name": "Updated HQ"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "property_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "tenant_id": "tenant-123",
        "name": "Updated HQ",
        "address": "Updated Street 1",
        "created_at": "2026-03-12T00:00:00+00:00",
    }


def test_update_property_rejects_invalid_property_uuid(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )

    event = {
        "rawPath": "/dev/properties/not-a-uuid",
        "body": json.dumps({"name": "Updated HQ"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "Invalid property ID."}


def test_update_property_maps_missing_property_to_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())

    def _raise_lookup_error(event, db, property_id):
        raise LookupError("Property not found for tenant.")

    monkeypatch.setattr(
        handler,
        "update_property",
        _raise_lookup_error,
        raising=False,
    )

    event = {
        "rawPath": "/dev/properties/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "body": json.dumps({"name": "Updated HQ"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"error": "Property not found for tenant."}


def test_update_lease_accepts_stage_prefixed_raw_path(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "update_lease",
        lambda event, db, lease_id: {
            "lease_id": str(lease_id),
            "tenant_id": "tenant-123",
            "property_id": "11111111-1111-1111-1111-111111111111",
            "resident_name": "Alice Updated",
            "rent_due_day_of_month": 7,
            "start_date": "2026-06-01",
            "end_date": "2027-05-31",
            "created_at": "2026-04-07T00:00:00+00:00",
        },
        raising=False,
    )

    event = {
        "rawPath": "/dev/leases/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "body": json.dumps({"resident_name": "Alice Updated"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "lease_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "tenant_id": "tenant-123",
        "property_id": "11111111-1111-1111-1111-111111111111",
        "resident_name": "Alice Updated",
        "rent_due_day_of_month": 7,
        "start_date": "2026-06-01",
        "end_date": "2027-05-31",
        "created_at": "2026-04-07T00:00:00+00:00",
    }


def test_update_lease_rejects_invalid_lease_uuid(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )

    event = {
        "rawPath": "/dev/leases/not-a-uuid",
        "body": json.dumps({"resident_name": "Alice Updated"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "Invalid lease ID."}


def test_update_lease_maps_missing_lease_to_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())

    def _raise_lookup_error(event, db, lease_id):
        raise LookupError("Lease not found for tenant.")

    monkeypatch.setattr(
        handler,
        "update_lease",
        _raise_lookup_error,
        raising=False,
    )

    event = {
        "rawPath": "/dev/leases/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "body": json.dumps({"resident_name": "Alice Updated"}),
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"error": "Lease not found for tenant."}


def test_mark_notification_read_maps_missing_notification_to_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())

    def _raise_lookup_error(event, db, notification_id):
        raise LookupError("Notification not found for tenant.")

    monkeypatch.setattr(
        handler,
        "mark_notification_read",
        _raise_lookup_error,
        raising=False,
    )

    event = {
        "rawPath": "/dev/notifications/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/read",
        "requestContext": {
            "stage": "dev",
            "http": {"method": "PATCH"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                        "custom:tenant_id": "tenant-123",
                    }
                }
            },
        },
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 404
    assert json.loads(response["body"]) == {"error": "Notification not found for tenant."}


def test_scan_due_lease_reminders_accepts_internal_event(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(handler, "Database", lambda settings: object())
    monkeypatch.setattr(
        handler,
        "scan_due_lease_reminders",
        lambda event, db: {"created_count": 1, "duplicate_count": 0},
        raising=False,
    )

    event = {
        "source": "leaseflow.internal",
        "detail-type": "scan_due_lease_reminders",
        "detail": {"tenant_id": "tenant-123"},
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "created_count": 1,
        "duplicate_count": 0,
    }


def test_run_db_migrations_accepts_internal_event(monkeypatch) -> None:
    monkeypatch.setattr(
        handler,
        "load_settings",
        lambda: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(
        handler,
        "run_db_migrations",
        lambda settings: {
            "target_revision": "head",
            "previous_revision": None,
            "current_revision": "20260407_0005",
        },
        raising=False,
    )

    event = {
        "source": "leaseflow.internal",
        "detail-type": "run_db_migrations",
        "detail": {},
    }

    response = handler.lambda_handler(event, SimpleNamespace(aws_request_id="test-id"))

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "target_revision": "head",
        "previous_revision": None,
        "current_revision": "20260407_0005",
    }
