#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
terraform_dev_init

API_URL="$(terraform_dev_output api_stage_invoke_url)"
COGNITO_HOSTED_UI="$(terraform_dev_output cognito_hosted_ui_base_url)"
COGNITO_CLIENT_ID="$(terraform_dev_output cognito_user_pool_client_id)"

cat > "${FRONTEND_DIR}/.env.local" <<EOF
VITE_API_BASE_URL=${API_URL}
VITE_COGNITO_HOSTED_UI_BASE_URL=${COGNITO_HOSTED_UI}
VITE_COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
EOF

info "Wrote frontend/.env.local"
info "Restart Vite after changing frontend/.env.local."
