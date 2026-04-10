from __future__ import annotations

import json
import re
from http import HTTPStatus
from typing import Any
from uuid import UUID

from app.auth import AuthError
from app.config import ConfigError, load_settings
from app.db import Database
from app.logging import get_logger, setup_logging
from app.routes.db_migrations import run_db_migrations
from app.routes.health import get_health
from app.routes.lease_reminders import list_due_lease_reminders
from app.routes.leases import create_lease, list_leases
from app.routes.notifications import list_notifications, mark_notification_read
from app.routes.properties import create_property, list_properties, update_property
from app.routes.reminder_scans import scan_due_lease_reminders

setup_logging()
LOGGER = get_logger(__name__)
_NOTIFICATION_READ_PATH = re.compile(r"^/notifications/(?P<notification_id>[^/]+)/read$")
_PROPERTY_PATH = re.compile(r"^/properties/(?P<property_id>[^/]+)$")


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


def _route_path(event: dict[str, Any]) -> str:
    raw_path = event.get("rawPath", "")
    stage = event.get("requestContext", {}).get("stage")
    if not stage:
        return raw_path

    stage_prefix = f"/{stage}"
    if raw_path == stage_prefix:
        return "/"
    if raw_path.startswith(f"{stage_prefix}/"):
        return raw_path[len(stage_prefix) :]
    return raw_path


def _notification_read_id(path: str) -> UUID | None:
    match = _NOTIFICATION_READ_PATH.fullmatch(path)
    if match is None:
        return None

    try:
        return UUID(match.group("notification_id"))
    except ValueError as exc:
        raise ValueError("Invalid notification ID.") from exc


def _property_id(path: str) -> UUID | None:
    match = _PROPERTY_PATH.fullmatch(path)
    if match is None:
        return None

    try:
        return UUID(match.group("property_id"))
    except ValueError as exc:
        raise ValueError("Invalid property ID.") from exc


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path = _route_path(event)
    request_id = getattr(context, "aws_request_id", None)
    LOGGER.info(
        "incoming_request",
        extra={"request_id": request_id},
    )

    try:
        if method == "GET" and path == "/health":
            return _response(HTTPStatus.OK, get_health())

        notification_id = _notification_read_id(path) if method == "PATCH" else None
        property_id = _property_id(path) if method == "PATCH" else None
        settings = load_settings()
        setup_logging(settings.log_level)
        if (
            event.get("source") == "leaseflow.internal"
            and event.get("detail-type") == "run_db_migrations"
        ):
            return _response(HTTPStatus.OK, run_db_migrations(settings))
        db = Database(settings)
        if (
            event.get("source") == "leaseflow.internal"
            and event.get("detail-type") == "scan_due_lease_reminders"
        ):
            return _response(HTTPStatus.OK, scan_due_lease_reminders(event, db))
        if method == "PATCH" and notification_id is not None:
            return _response(HTTPStatus.OK, mark_notification_read(event, db, notification_id))
        if method == "PATCH" and property_id is not None:
            return _response(HTTPStatus.OK, update_property(event, db, property_id))
        if method == "GET" and path == "/notifications":
            return _response(HTTPStatus.OK, list_notifications(event, db))
        if method == "GET" and path == "/lease-reminders/due-soon":
            return _response(HTTPStatus.OK, list_due_lease_reminders(event, db))
        if method == "GET" and path == "/leases":
            return _response(HTTPStatus.OK, list_leases(event, db))
        if method == "POST" and path == "/leases":
            return _response(HTTPStatus.CREATED, create_lease(event, db, _json_body(event)))
        if method == "GET" and path == "/properties":
            return _response(HTTPStatus.OK, list_properties(event, db))
        if method == "POST" and path == "/properties":
            return _response(HTTPStatus.CREATED, create_property(event, db, _json_body(event)))

        return _response(HTTPStatus.NOT_FOUND, {"error": "Route not found"})
    except LookupError as exc:
        LOGGER.warning("request_rejected", extra={"request_id": request_id})
        return _response(HTTPStatus.NOT_FOUND, {"error": str(exc)})
    except (ValueError, AuthError, ConfigError) as exc:
        LOGGER.warning("request_rejected", extra={"request_id": request_id})
        return _response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
    except Exception:
        LOGGER.exception("unhandled_error", extra={"request_id": request_id})
        return _response(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})
