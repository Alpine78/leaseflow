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
