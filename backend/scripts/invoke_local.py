from __future__ import annotations

import argparse
import json
from types import SimpleNamespace
from typing import Any

from app import handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Invoke the Lambda handler locally.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Invoke GET /health.")

    list_parser = subparsers.add_parser("list-properties", help="Invoke GET /properties.")
    list_parser.add_argument("--tenant-id", default="tenant-local")
    list_parser.add_argument("--user-id", default="user-local")

    reminders_parser = subparsers.add_parser(
        "list-due-lease-reminders",
        help="Invoke GET /lease-reminders/due-soon.",
    )
    reminders_parser.add_argument("--tenant-id", default="tenant-local")
    reminders_parser.add_argument("--user-id", default="user-local")
    reminders_parser.add_argument("--days", type=int, default=7)

    scan_parser = subparsers.add_parser(
        "scan-due-lease-reminders",
        help="Invoke internal due lease reminder scan.",
    )
    scan_parser.add_argument("--tenant-id")
    scan_parser.add_argument("--days", type=int, default=7)
    scan_parser.add_argument("--as-of-date")

    create_parser = subparsers.add_parser("create-property", help="Invoke POST /properties.")
    create_parser.add_argument("--tenant-id", default="tenant-local")
    create_parser.add_argument("--user-id", default="user-local")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--address", required=True)

    return parser.parse_args(argv)


def build_event(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "health":
        return {
            "rawPath": "/health",
            "requestContext": {"http": {"method": "GET"}},
        }

    if args.command == "scan-due-lease-reminders":
        detail: dict[str, Any] = {"days": args.days}
        if args.tenant_id:
            detail["tenant_id"] = args.tenant_id
        if args.as_of_date:
            detail["as_of_date"] = args.as_of_date
        return {
            "source": "leaseflow.internal",
            "detail-type": "scan_due_lease_reminders",
            "detail": detail,
        }

    raw_path = (
        "/lease-reminders/due-soon"
        if args.command == "list-due-lease-reminders"
        else "/properties"
    )
    event = {
        "rawPath": raw_path,
        "requestContext": {
            "http": {"method": "GET" if args.command == "list-properties" else "POST"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": args.user_id,
                        "custom:tenant_id": args.tenant_id,
                    }
                }
            },
        },
    }

    if args.command == "list-due-lease-reminders":
        event["requestContext"]["http"]["method"] = "GET"
        event["queryStringParameters"] = {"days": str(args.days)}
        return event

    if args.command == "create-property":
        event["body"] = json.dumps({"name": args.name, "address": args.address})

    return event


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    event = build_event(args)
    response = handler.lambda_handler(
        event,
        SimpleNamespace(aws_request_id="local-invoke"),
    )
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
