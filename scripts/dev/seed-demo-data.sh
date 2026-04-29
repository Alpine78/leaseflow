#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command curl
require_command python3
terraform_dev_init

API_URL="$(terraform_dev_output api_stage_invoke_url)"
API_URL="${API_URL%/}"
USER_POOL_ID="$(terraform_dev_output cognito_user_pool_id)"
APP_CLIENT_ID="$(terraform_dev_output cognito_user_pool_client_id)"
BACKEND_FUNCTION="${BACKEND_FUNCTION:-leaseflow-dev-backend}"

SEED_STAMP="${SEED_STAMP:-$(date -u +%Y%m%d%H%M%S)}"
SEED_EMAIL="${SEED_EMAIL:-seed-demo-${SEED_STAMP}@example.com}"
SEED_TENANT="${SEED_TENANT:-seed-demo-${SEED_STAMP}}"
SEED_PASSWORD="${SEED_PASSWORD:-$(python3 - <<'PY'
import secrets
import string

chars = string.ascii_letters + string.digits
print("Lf-" + "".join(secrets.choice(chars) for _ in range(18)) + "!Aa1")
PY
)}"

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

write_property_payload() {
  local payload_file="$1"
  local name="$2"
  local address="$3"

  python3 - "${payload_file}" "${name}" "${address}" <<'PY'
import json
import sys

payload = {
    "name": sys.argv[2],
    "address": sys.argv[3],
}

with open(sys.argv[1], "w", encoding="utf-8") as payload_file:
    json.dump(payload, payload_file)
PY
}

write_lease_payload() {
  local payload_file="$1"
  local property_id="$2"
  local resident_name="$3"
  local rent_due_day="$4"
  local start_date="$5"
  local end_date="$6"

  python3 - \
    "${payload_file}" \
    "${property_id}" \
    "${resident_name}" \
    "${rent_due_day}" \
    "${start_date}" \
    "${end_date}" <<'PY'
import json
import sys

payload = {
    "property_id": sys.argv[2],
    "resident_name": sys.argv[3],
    "rent_due_day_of_month": int(sys.argv[4]),
    "start_date": sys.argv[5],
    "end_date": sys.argv[6],
}

with open(sys.argv[1], "w", encoding="utf-8") as payload_file:
    json.dump(payload, payload_file)
PY
}

info "Creating temporary Cognito seed user"
aws cognito-idp admin-create-user \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${SEED_EMAIL}" \
  --user-attributes \
    Name=email,Value="${SEED_EMAIL}" \
    Name=email_verified,Value=true \
    Name=custom:tenant_id,Value="${SEED_TENANT}" \
  --message-action SUPPRESS >/dev/null

aws cognito-idp admin-set-user-password \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${SEED_EMAIL}" \
  --password "${SEED_PASSWORD}" \
  --permanent >/dev/null

ID_TOKEN="$(
  aws cognito-idp admin-initiate-auth \
    --user-pool-id "${USER_POOL_ID}" \
    --client-id "${APP_CLIENT_ID}" \
    --auth-flow ADMIN_USER_PASSWORD_AUTH \
    --auth-parameters USERNAME="${SEED_EMAIL}",PASSWORD="${SEED_PASSWORD}" \
    --query 'AuthenticationResult.IdToken' \
    --output text
)"

[[ -n "${ID_TOKEN}" && "${ID_TOKEN}" != "None" ]] || die "Could not obtain Cognito ID token."

TODAY="$(date -u +%Y-%m-%d)"
START_DATE="$(date -u -d "-7 days" +%Y-%m-%d)"
END_DATE="$(date -u -d "+120 days" +%Y-%m-%d)"
RENT_DUE_DAY="$(date -u +%-d)"
FUTURE_RENT_DUE_DAY="$(python3 - "${RENT_DUE_DAY}" <<'PY'
import sys

day = int(sys.argv[1])
print(20 if day <= 10 else 5)
PY
)"

PROPERTY_ONE_PAYLOAD="${TMP_DIR}/property-one.json"
PROPERTY_ONE_RESPONSE="${TMP_DIR}/property-one-response.json"
PROPERTY_TWO_PAYLOAD="${TMP_DIR}/property-two.json"
PROPERTY_TWO_RESPONSE="${TMP_DIR}/property-two-response.json"
LEASE_ONE_PAYLOAD="${TMP_DIR}/lease-one.json"
LEASE_ONE_RESPONSE="${TMP_DIR}/lease-one-response.json"
LEASE_TWO_PAYLOAD="${TMP_DIR}/lease-two.json"
LEASE_TWO_RESPONSE="${TMP_DIR}/lease-two-response.json"
REMINDER_SCAN_PAYLOAD="${TMP_DIR}/reminder-scan.json"
REMINDER_SCAN_RESPONSE="${TMP_DIR}/reminder-scan-response.json"

write_property_payload "${PROPERTY_ONE_PAYLOAD}" "Demo Harbor Flats" "Demo Harbor Street 12"
api_post_json "/properties" "${PROPERTY_ONE_PAYLOAD}" "${PROPERTY_ONE_RESPONSE}"
PROPERTY_ONE_ID="$(json_field "${PROPERTY_ONE_RESPONSE}" "property_id")"

write_property_payload "${PROPERTY_TWO_PAYLOAD}" "Demo Forest Homes" "Demo Forest Road 8"
api_post_json "/properties" "${PROPERTY_TWO_PAYLOAD}" "${PROPERTY_TWO_RESPONSE}"
PROPERTY_TWO_ID="$(json_field "${PROPERTY_TWO_RESPONSE}" "property_id")"

write_lease_payload \
  "${LEASE_ONE_PAYLOAD}" \
  "${PROPERTY_ONE_ID}" \
  "Demo Resident One" \
  "${RENT_DUE_DAY}" \
  "${START_DATE}" \
  "${END_DATE}"
api_post_json "/leases" "${LEASE_ONE_PAYLOAD}" "${LEASE_ONE_RESPONSE}"

write_lease_payload \
  "${LEASE_TWO_PAYLOAD}" \
  "${PROPERTY_TWO_ID}" \
  "Demo Resident Two" \
  "${FUTURE_RENT_DUE_DAY}" \
  "${TODAY}" \
  "${END_DATE}"
api_post_json "/leases" "${LEASE_TWO_PAYLOAD}" "${LEASE_TWO_RESPONSE}"

python3 - "${REMINDER_SCAN_PAYLOAD}" "${SEED_TENANT}" "${TODAY}" <<'PY'
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

printf 'EMAIL=%s\n' "${SEED_EMAIL}"
printf 'PASSWORD=%s\n' "${SEED_PASSWORD}"
printf 'PROPERTY_CREATED_COUNT=%s\n' "2"
printf 'LEASE_CREATED_COUNT=%s\n' "2"
echo "Seed data is synthetic and disposable. Do not commit or paste credentials into evidence."
