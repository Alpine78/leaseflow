#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command curl
require_command python3

if [[ $# -gt 1 ]]; then
  die "Usage: IMPORT_EMAIL=... IMPORT_PASSWORD=... IMPORT_FILE=... bash scripts/dev/import-tenant-data.sh"
fi

IMPORT_FILE="${1:-${IMPORT_FILE:-}}"
[[ -n "${IMPORT_FILE}" ]] || die "Set IMPORT_FILE or pass the export file path as the first argument."
require_file "${IMPORT_FILE}"
[[ -n "${IMPORT_EMAIL:-}" ]] || die "Set IMPORT_EMAIL for the target Cognito user."
[[ -n "${IMPORT_PASSWORD:-}" ]] || die "Set IMPORT_PASSWORD for the target Cognito user."

terraform_dev_init

API_URL="$(terraform_dev_output api_stage_invoke_url)"
API_URL="${API_URL%/}"
USER_POOL_ID="$(terraform_dev_output cognito_user_pool_id)"
APP_CLIENT_ID="$(terraform_dev_output cognito_user_pool_client_id)"
BACKEND_FUNCTION="${BACKEND_FUNCTION:-leaseflow-dev-backend}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

json_field() {
  local file_path="$1"
  local field_name="$2"
  python3 - "${file_path}" "${field_name}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as response_file:
    payload = json.load(response_file)

value = payload[sys.argv[2]]
print(value)
PY
}

api_post_json() {
  local route="$1"
  local payload_file="$2"
  local response_file="$3"
  local status_code

  status_code="$(
    curl -sS \
      -X POST \
      -H "Authorization: Bearer ${ID_TOKEN}" \
      -H "Content-Type: application/json" \
      -d @"${payload_file}" \
      -o "${response_file}" \
      -w "%{http_code}" \
      "${API_URL}${route}"
  )"

  if [[ "${status_code}" != "201" ]]; then
    die "POST ${route} failed with HTTP ${status_code}."
  fi
}

ID_TOKEN="$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "${USER_POOL_ID}" \
    --client-id "${APP_CLIENT_ID}" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="${IMPORT_EMAIL}",PASSWORD="${IMPORT_PASSWORD}" \
    --query 'AuthenticationResult.IdToken' \
    --output text
)"

[[ -n "${ID_TOKEN}" && "${ID_TOKEN}" != "None" ]] || die "Could not obtain Cognito ID token."

TENANT_ID_FILE="${TMP_DIR}/tenant-id.txt"
python3 - "${ID_TOKEN}" "${TENANT_ID_FILE}" <<'PY'
import base64
import json
import sys

parts = sys.argv[1].split(".")
if len(parts) < 2:
    raise SystemExit("Invalid ID token.")

payload = parts[1] + "=" * (-len(parts[1]) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
tenant_id = claims.get("custom:tenant_id")
if not isinstance(tenant_id, str) or not tenant_id.strip():
    raise SystemExit("ID token does not contain custom:tenant_id.")

with open(sys.argv[2], "w", encoding="utf-8") as tenant_file:
    tenant_file.write(tenant_id)
PY
TENANT_ID="$(cat "${TENANT_ID_FILE}")"

PROPERTY_MANIFEST="${TMP_DIR}/properties-manifest.tsv"
PROPERTY_MAP="${TMP_DIR}/property-map.tsv"
LEASE_MANIFEST="${TMP_DIR}/leases-manifest.tsv"
NOTIFICATION_COUNT_FILE="${TMP_DIR}/notification-count.txt"
touch "${PROPERTY_MAP}"

python3 - "${IMPORT_FILE}" "${TMP_DIR}" "${PROPERTY_MANIFEST}" "${NOTIFICATION_COUNT_FILE}" <<'PY'
from __future__ import annotations

import json
import os
import sys


def require_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    items = payload.get(key)
    if not isinstance(items, list):
        raise SystemExit(f"Export file does not contain a {key} list.")
    for item in items:
        if not isinstance(item, dict):
            raise SystemExit(f"Export file {key} contains a non-object item.")
    return items


with open(sys.argv[1], encoding="utf-8") as export_file:
    payload = json.load(export_file)

if payload.get("schema_version") != 1:
    raise SystemExit("Only export schema_version 1 is supported.")

properties = require_list(payload, "properties")
notifications = require_list(payload, "notifications")

with open(sys.argv[3], "w", encoding="utf-8") as manifest:
    for index, item in enumerate(properties, start=1):
        old_property_id = item.get("property_id")
        name = item.get("name")
        address = item.get("address")
        if not all(isinstance(value, str) and value.strip() for value in (old_property_id, name, address)):
            raise SystemExit("Each exported property must contain property_id, name, and address.")

        payload_path = os.path.join(sys.argv[2], f"property-{index}.json")
        with open(payload_path, "w", encoding="utf-8") as payload_file:
            json.dump({"name": name, "address": address}, payload_file)

        manifest.write(f"{old_property_id}\t{payload_path}\n")

with open(sys.argv[4], "w", encoding="utf-8") as count_file:
    count_file.write(str(len(notifications)))
PY

info "Importing properties through tenant-scoped API"
PROPERTY_IMPORTED_COUNT=0
while IFS=$'\t' read -r old_property_id property_payload_file; do
  response_file="${TMP_DIR}/property-${PROPERTY_IMPORTED_COUNT}-response.json"
  api_post_json "/properties" "${property_payload_file}" "${response_file}"
  new_property_id="$(json_field "${response_file}" "property_id")"
  printf '%s\t%s\n' "${old_property_id}" "${new_property_id}" >>"${PROPERTY_MAP}"
  PROPERTY_IMPORTED_COUNT=$((PROPERTY_IMPORTED_COUNT + 1))
done <"${PROPERTY_MANIFEST}"

python3 - "${IMPORT_FILE}" "${TMP_DIR}" "${PROPERTY_MAP}" "${LEASE_MANIFEST}" <<'PY'
from __future__ import annotations

import json
import os
import sys


def require_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    items = payload.get(key)
    if not isinstance(items, list):
        raise SystemExit(f"Export file does not contain a {key} list.")
    for item in items:
        if not isinstance(item, dict):
            raise SystemExit(f"Export file {key} contains a non-object item.")
    return items


with open(sys.argv[1], encoding="utf-8") as export_file:
    payload = json.load(export_file)

leases = require_list(payload, "leases")
property_map: dict[str, str] = {}
with open(sys.argv[3], encoding="utf-8") as map_file:
    for line in map_file:
        old_property_id, new_property_id = line.rstrip("\n").split("\t", 1)
        property_map[old_property_id] = new_property_id

with open(sys.argv[4], "w", encoding="utf-8") as manifest:
    for index, item in enumerate(leases, start=1):
        old_property_id = item.get("property_id")
        if not isinstance(old_property_id, str) or old_property_id not in property_map:
            raise SystemExit("Each exported lease must reference an exported property_id.")

        resident_name = item.get("resident_name")
        rent_due_day = item.get("rent_due_day_of_month")
        start_date = item.get("start_date")
        end_date = item.get("end_date")
        if not isinstance(resident_name, str) or not resident_name.strip():
            raise SystemExit("Each exported lease must contain resident_name.")
        if not isinstance(rent_due_day, int):
            raise SystemExit("Each exported lease must contain integer rent_due_day_of_month.")
        if not isinstance(start_date, str) or not start_date.strip():
            raise SystemExit("Each exported lease must contain start_date.")
        if not isinstance(end_date, str) or not end_date.strip():
            raise SystemExit("Each exported lease must contain end_date.")

        payload_path = os.path.join(sys.argv[2], f"lease-{index}.json")
        with open(payload_path, "w", encoding="utf-8") as payload_file:
            json.dump(
                {
                    "property_id": property_map[old_property_id],
                    "resident_name": resident_name,
                    "rent_due_day_of_month": rent_due_day,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                payload_file,
            )

        manifest.write(f"{payload_path}\n")
PY

info "Importing leases through tenant-scoped API"
LEASE_IMPORTED_COUNT=0
while IFS= read -r lease_payload_file; do
  response_file="${TMP_DIR}/lease-${LEASE_IMPORTED_COUNT}-response.json"
  api_post_json "/leases" "${lease_payload_file}" "${response_file}"
  LEASE_IMPORTED_COUNT=$((LEASE_IMPORTED_COUNT + 1))
done <"${LEASE_MANIFEST}"

TODAY="$(date -u +%Y-%m-%d)"
REMINDER_SCAN_PAYLOAD="${TMP_DIR}/reminder-scan.json"
REMINDER_SCAN_RESPONSE="${TMP_DIR}/reminder-scan-response.json"

python3 - "${REMINDER_SCAN_PAYLOAD}" "${TENANT_ID}" "${TODAY}" <<'PY'
import json
import sys

payload = {
    "source": "leaseflow.internal",
    "detail-type": "scan_due_lease_reminders",
    "detail": {
        "tenant_id": sys.argv[2],
        "days": 7,
        "as_of_date": sys.argv[3],
    },
}

with open(sys.argv[1], "w", encoding="utf-8") as payload_file:
    json.dump(payload, payload_file)
PY

info "Regenerating due notifications with the internal reminder scan"
aws lambda invoke \
  --region "${AWS_REGION}" \
  --function-name "${BACKEND_FUNCTION}" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${REMINDER_SCAN_PAYLOAD}" \
  "${REMINDER_SCAN_RESPONSE}" \
  --query 'StatusCode' \
  --output text >/dev/null

python3 - "${REMINDER_SCAN_RESPONSE}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as response_file:
    payload = json.load(response_file)

status_code = payload.get("statusCode")
body = payload.get("body")
if isinstance(body, str):
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        body = {}

if not isinstance(body, dict):
    body = {}

print(f"REMINDER_SCAN_STATUS_CODE={status_code}")
print(f"REMINDER_CANDIDATE_COUNT={body.get('candidate_count', 0)}")
print(f"NOTIFICATION_CREATED_COUNT={body.get('created_count', 0)}")
print(f"NOTIFICATION_DUPLICATE_COUNT={body.get('duplicate_count', 0)}")

if status_code != 200:
    sys.exit(1)
PY

printf 'PROPERTY_IMPORTED_COUNT=%s\n' "${PROPERTY_IMPORTED_COUNT}"
printf 'LEASE_IMPORTED_COUNT=%s\n' "${LEASE_IMPORTED_COUNT}"
printf 'NOTIFICATION_SNAPSHOT_COUNT=%s\n' "$(cat "${NOTIFICATION_COUNT_FILE}")"
echo "Notification rows are not imported directly; due notifications are regenerated from imported leases."
