#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command python3
terraform_dev_init

USER_POOL_ID="$(terraform_dev_output cognito_user_pool_id)"
DEMO_STAMP="${DEMO_STAMP:-$(date -u +%Y%m%d%H%M%S)}"
DEMO_EMAIL="${DEMO_EMAIL:-browser-demo-${DEMO_STAMP}@example.com}"
DEMO_TENANT="${DEMO_TENANT:-browser-demo-${DEMO_STAMP}}"
DEMO_PASSWORD="${DEMO_PASSWORD:-$(python3 - <<'PY'
import secrets
import string

chars = string.ascii_letters + string.digits
print("Lf-" + "".join(secrets.choice(chars) for _ in range(18)) + "!Aa1")
PY
)}"

info "Creating temporary Cognito browser demo user"
aws cognito-idp admin-create-user \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${DEMO_EMAIL}" \
  --user-attributes \
    Name=email,Value="${DEMO_EMAIL}" \
    Name=email_verified,Value=true \
    Name=custom:tenant_id,Value="${DEMO_TENANT}" \
  --message-action SUPPRESS >/dev/null

aws cognito-idp admin-set-user-password \
  --user-pool-id "${USER_POOL_ID}" \
  --username "${DEMO_EMAIL}" \
  --password "${DEMO_PASSWORD}" \
  --permanent >/dev/null

printf 'EMAIL=%s\n' "${DEMO_EMAIL}"
printf 'PASSWORD=%s\n' "${DEMO_PASSWORD}"
echo "Do not commit or paste these temporary credentials into evidence."
