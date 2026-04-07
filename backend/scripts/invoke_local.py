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

    event = {
        "rawPath": "/properties",
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
