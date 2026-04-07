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
