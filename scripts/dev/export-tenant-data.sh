#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command curl
require_command python3

[[ -n "${EXPORT_EMAIL:-}" ]] || die "Set EXPORT_EMAIL for the Cognito user whose tenant data is exported."
[[ -n "${EXPORT_PASSWORD:-}" ]] || die "Set EXPORT_PASSWORD for the Cognito user whose tenant data is exported."

terraform_dev_init

API_URL="$(terraform_dev_output api_stage_invoke_url)"
API_URL="${API_URL%/}"
USER_POOL_ID="$(terraform_dev_output cognito_user_pool_id)"
APP_CLIENT_ID="$(terraform_dev_output cognito_user_pool_client_id)"
EXPORT_DIR="${EXPORT_DIR:-${REPO_ROOT}/.local/leaseflow-export}"
EXPORT_STAMP="${EXPORT_STAMP:-$(date -u +%Y%m%d%H%M%S)}"
EXPORT_FILE="${EXPORT_FILE:-${EXPORT_DIR}/leaseflow-export-${EXPORT_STAMP}.json}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

api_get_json() {
  local route="$1"
  local response_file="$2"
  local status_code

  status_code="$(
    curl -sS \
      -H "Authorization: Bearer ${ID_TOKEN}" \
      -H "Content-Type: application/json" \
      -o "${response_file}" \
      -w "%{http_code}" \
      "${API_URL}${route}"
  )"

  if [[ "${status_code}" != "200" ]]; then
    die "GET ${route} failed with HTTP ${status_code}."
  fi
}

ID_TOKEN="$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "${USER_POOL_ID}" \
    --client-id "${APP_CLIENT_ID}" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="${EXPORT_EMAIL}",PASSWORD="${EXPORT_PASSWORD}" \
    --query 'AuthenticationResult.IdToken' \
    --output text
)"

[[ -n "${ID_TOKEN}" && "${ID_TOKEN}" != "None" ]] || die "Could not obtain Cognito ID token."

PROPERTIES_RESPONSE="${TMP_DIR}/properties.json"
LEASES_RESPONSE="${TMP_DIR}/leases.json"
NOTIFICATIONS_RESPONSE="${TMP_DIR}/notifications.json"

info "Reading tenant-scoped API data"
api_get_json "/properties" "${PROPERTIES_RESPONSE}"
api_get_json "/leases" "${LEASES_RESPONSE}"
api_get_json "/notifications" "${NOTIFICATIONS_RESPONSE}"

mkdir -p "$(dirname -- "${EXPORT_FILE}")"

python3 - \
  "${PROPERTIES_RESPONSE}" \
  "${LEASES_RESPONSE}" \
  "${NOTIFICATIONS_RESPONSE}" \
  "${EXPORT_FILE}" <<'PY'
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys


def load_items(path: str) -> list[dict[str, object]]:
    with open(path, encoding="utf-8") as response_file:
        response = json.load(response_file)

    items = response.get("items")
    if not isinstance(items, list):
        raise SystemExit(f"Response {path} does not contain an items list.")
    return items


def copy_known_fields(item: dict[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: item[field] for field in fields if field in item}


properties = [
    copy_known_fields(item, ("property_id", "name", "address", "created_at"))
    for item in load_items(sys.argv[1])
]
leases = [
    copy_known_fields(
        item,
        (
            "lease_id",
            "property_id",
            "resident_name",
            "rent_due_day_of_month",
            "start_date",
            "end_date",
            "created_at",
        ),
    )
    for item in load_items(sys.argv[2])
]
notifications = [
    copy_known_fields(
        item,
        (
            "notification_id",
            "lease_id",
            "type",
            "title",
            "message",
            "due_date",
            "created_at",
            "read_at",
        ),
    )
    for item in load_items(sys.argv[3])
]

export_payload = {
    "schema_version": 1,
    "exported_at": datetime.now(timezone.utc).isoformat(),
    "source": {
        "kind": "leaseflow-dev-api",
        "notifications": "snapshot-only",
    },
    "properties": properties,
    "leases": leases,
    "notifications": notifications,
}

with open(sys.argv[4], "w", encoding="utf-8") as export_file:
    json.dump(export_payload, export_file, indent=2)
    export_file.write("\n")
PY

python3 - "${EXPORT_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as export_file:
    payload = json.load(export_file)

print(f"EXPORT_FILE={sys.argv[1]}")
print(f"PROPERTY_EXPORTED_COUNT={len(payload.get('properties', []))}")
print(f"LEASE_EXPORTED_COUNT={len(payload.get('leases', []))}")
print(f"NOTIFICATION_EXPORTED_COUNT={len(payload.get('notifications', []))}")
PY

echo "Export files may contain tenant-scoped demo data. Do not commit or paste them into evidence."
