#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command python3
terraform_dev_init

BACKEND_FUNCTION="${BACKEND_FUNCTION:-leaseflow-dev-backend}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

PAYLOAD_FILE="${TMP_DIR}/migration-payload.json"
RESPONSE_FILE="${TMP_DIR}/migration-response.json"

cat > "${PAYLOAD_FILE}" <<'JSON'
{"source":"leaseflow.internal","detail-type":"run_db_migrations","detail":{}}
JSON

info "Invoking deployed DB migrations through ${BACKEND_FUNCTION}"
aws lambda invoke \
  --region "${AWS_REGION}" \
  --function-name "${BACKEND_FUNCTION}" \
  --cli-binary-format raw-in-base64-out \
  --payload "fileb://${PAYLOAD_FILE}" \
  "${RESPONSE_FILE}" \
  --query 'StatusCode' \
  --output text >/dev/null

python3 - "${RESPONSE_FILE}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as response_file:
    payload = json.load(response_file)

status_code = payload.get("statusCode")
print(f"MIGRATION_STATUS_CODE={status_code}")

body = payload.get("body")
if isinstance(body, str):
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        body = {}

if isinstance(body, dict):
    for key in ("previous_revision", "target_revision", "current_revision"):
        value = body.get(key)
        if value is not None:
            print(f"{key.upper()}={value}")

if status_code != 200:
    sys.exit(1)
PY
