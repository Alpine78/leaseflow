from __future__ import annotations

import json
from typing import Any

from scripts import invoke_local


def test_build_event_for_list_properties_uses_jwt_claims() -> None:
    args = invoke_local.parse_args(
        [
            "list-properties",
            "--tenant-id",
            "tenant-local",
            "--user-id",
            "user-local",
        ]
    )

    event = invoke_local.build_event(args)

    assert event == {
        "rawPath": "/properties",
        "requestContext": {
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-local",
                        "custom:tenant_id": "tenant-local",
                    }
                }
            },
        },
    }


def test_build_event_for_create_property_uses_body_and_jwt_claims() -> None:
    args = invoke_local.parse_args(
        [
            "create-property",
            "--tenant-id",
            "tenant-local",
            "--user-id",
            "user-local",
            "--name",
            "HQ",
            "--address",
            "Main Street 1",
        ]
    )

    event = invoke_local.build_event(args)

    assert event["rawPath"] == "/properties"
    assert event["requestContext"]["http"]["method"] == "POST"
    assert event["requestContext"]["authorizer"]["jwt"]["claims"] == {
        "sub": "user-local",
        "custom:tenant_id": "tenant-local",
    }
    assert json.loads(event["body"]) == {
        "name": "HQ",
        "address": "Main Street 1",
    }


def test_build_event_for_list_due_lease_reminders_uses_query_and_jwt_claims() -> None:
    args = invoke_local.parse_args(
        [
            "list-due-lease-reminders",
            "--tenant-id",
            "tenant-local",
            "--user-id",
            "user-local",
            "--days",
            "14",
        ]
    )

    event = invoke_local.build_event(args)

    assert event == {
        "rawPath": "/lease-reminders/due-soon",
        "queryStringParameters": {"days": "14"},
        "requestContext": {
            "http": {"method": "GET"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-local",
                        "custom:tenant_id": "tenant-local",
                    }
                }
            },
        },
    }


def test_build_event_for_scan_due_lease_reminders_uses_internal_detail() -> None:
    args = invoke_local.parse_args(
        [
            "scan-due-lease-reminders",
            "--days",
            "14",
            "--as-of-date",
            "2026-04-09",
        ]
    )

    event = invoke_local.build_event(args)

    assert event == {
        "source": "leaseflow.internal",
        "detail-type": "scan_due_lease_reminders",
        "detail": {
            "days": 14,
            "as_of_date": "2026-04-09",
        },
    }


def test_main_invokes_lambda_handler_and_prints_response(monkeypatch: Any, capsys: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
        captured["event"] = event
        captured["request_id"] = context.aws_request_id
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok"}),
        }

    monkeypatch.setattr(invoke_local.handler, "lambda_handler", _fake_handler)

    exit_code = invoke_local.main(["health"])

    assert exit_code == 0
    assert captured["event"] == {
        "rawPath": "/health",
        "requestContext": {"http": {"method": "GET"}},
    }
    assert captured["request_id"] == "local-invoke"
    assert json.loads(capsys.readouterr().out) == {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status": "ok"}',
    }
