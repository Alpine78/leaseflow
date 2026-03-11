from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from app.auth import AuthError
from app.config import ConfigError, load_settings
from app.db import Database
from app.logging import get_logger, setup_logging
from app.routes.health import get_health
from app.routes.properties import create_property, list_properties

setup_logging()
LOGGER = get_logger(__name__)


def _response(status: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": int(status),
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw in (None, ""):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON request body.") from exc


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = event.get("rawPath", "")
    request_id = getattr(context, "aws_request_id", None)
    LOGGER.info(
        "incoming_request",
        extra={"request_id": request_id},
    )

    try:
        if method == "GET" and path == "/health":
            return _response(HTTPStatus.OK, get_health())

        settings = load_settings()
        setup_logging(settings.log_level)
        db = Database(settings)
        if method == "GET" and path == "/properties":
            return _response(HTTPStatus.OK, list_properties(event, db))
        if method == "POST" and path == "/properties":
            return _response(HTTPStatus.CREATED, create_property(event, db, _json_body(event)))

        return _response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
    except (ValueError, AuthError, ConfigError) as exc:
        LOGGER.warning("request_rejected", extra={"request_id": request_id})
        return _response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
    except Exception:
        LOGGER.exception("unhandled_error", extra={"request_id": request_id})
        return _response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})
