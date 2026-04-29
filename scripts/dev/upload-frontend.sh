#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command aws
require_command npm
require_file "${FRONTEND_DIR}/.env.local"
terraform_dev_init

FRONTEND_BUCKET="$(terraform_dev_output frontend_bucket_name)"
FRONTEND_DISTRIBUTION_ID="$(terraform_dev_output frontend_cloudfront_distribution_id)"
FRONTEND_URL="$(terraform_dev_output frontend_cloudfront_url)"

info "Building frontend"
npm --prefix "${FRONTEND_DIR}" run build

info "Uploading frontend assets"
aws s3 sync "${FRONTEND_DIR}/dist/" "s3://${FRONTEND_BUCKET}/" --delete

info "Invalidating CloudFront distribution"
aws cloudfront create-invalidation \
  --distribution-id "${FRONTEND_DISTRIBUTION_ID}" \
  --paths "/*" \
  --query 'Invalidation.{Id:Id,Status:Status}' \
  --output table

printf 'FRONTEND_URL=%s\n' "${FRONTEND_URL}"
