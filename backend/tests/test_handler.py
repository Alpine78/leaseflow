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
