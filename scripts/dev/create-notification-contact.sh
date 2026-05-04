#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command python3
terraform_dev_init

CONTACT_COGNITO_USERNAME="${CONTACT_COGNITO_USERNAME:-}"
CONTACT_EMAIL="${CONTACT_EMAIL:-}"
BACKEND_FUNCTION="${BACKEND_FUNCTION:-leaseflow-dev-backend}"

[[ -n "${CONTACT_COGNITO_USERNAME}" ]] || die "Set CONTACT_COGNITO_USERNAME to the existing Cognito username for the smoke tenant."
[[ -n "${CONTACT_EMAIL}" ]] || die "Set CONTACT_EMAIL to the verified SES smoke recipient email."

USER_POOL_ID="$(terraform_dev_output cognito_user_pool_id)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

PAYLOAD_FILE="${TMP_DIR}/notification-contact-payload.json"
RESPONSE_FILE="${TMP_DIR}/notification-contact-response.json"

CONTACT_TENANT="$(
  aws cognito-idp admin-get-user \
    --user-pool-id "${USER_POOL_ID}" \
    --username "${CONTACT_COGNITO_USERNAME}" \
    --query 'UserAttributes[?Name==`custom:tenant_id`].Value | [0]' \
    --output text
)"

[[ -n "${CONTACT_TENANT}" && "${CONTACT_TENANT}" != "None" ]] || die "Could not resolve custom:tenant_id for CONTACT_COGNITO_USERNAME."

python3 - "${PAYLOAD_FILE}" "${CONTACT_TENANT}" "${CONTACT_EMAIL}" <<'PY'
import json
import sys

payload = {
    "source": "leaseflow.internal",
    "detail-type": "configure_notification_contact",
    "detail": {
        "tenant_id": sys.argv[2],
        "email": sys.argv[3],
    },
}

with open(sys.argv[1], "w", encoding="utf-8") as payload_file:
    json.dump(payload, payload_file)
PY

info "Configuring notification contact through ${BACKEND_FUNCTION}"
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
print(f"CONTACT_SETUP_STATUS_CODE={status_code}")

body = payload.get("body")
if isinstance(body, str):
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        body = {}

if isinstance(body, dict):
    for source_key, output_key in (
        ("configured", "CONTACT_CONFIGURED"),
        ("created", "CONTACT_CREATED"),
        ("updated", "CONTACT_UPDATED"),
        ("enabled", "CONTACT_ENABLED"),
    ):
        if source_key in body:
            print(f"{output_key}={str(body[source_key]).lower()}")

if status_code != 200:
    sys.exit(1)
PY

echo "Do not commit or paste CONTACT_EMAIL, CONTACT_COGNITO_USERNAME, or tenant values into evidence."
