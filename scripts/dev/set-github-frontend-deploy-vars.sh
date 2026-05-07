#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command gh
terraform_dev_init

GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-Alpine78/leaseflow}"
GITHUB_ENVIRONMENT="${GITHUB_ENVIRONMENT:-dev}"

set_github_variable() {
  local name="$1"
  local value="$2"

  printf '%s' "${value}" | gh variable set "${name}" \
    --repo "${GITHUB_REPOSITORY}" \
    --env "${GITHUB_ENVIRONMENT}" >/dev/null
  printf 'SET_GITHUB_ENV_VAR=%s\n' "${name}"
}

info "Setting GitHub Environment variables for ${GITHUB_REPOSITORY}:${GITHUB_ENVIRONMENT}"

set_github_variable "AWS_REGION" "${AWS_REGION}"
set_github_variable "FRONTEND_DEPLOY_ROLE_ARN" "$(terraform_dev_output frontend_deploy_role_arn)"
set_github_variable "FRONTEND_BUCKET_NAME" "$(terraform_dev_output frontend_bucket_name)"
set_github_variable "FRONTEND_CLOUDFRONT_DISTRIBUTION_ID" "$(terraform_dev_output frontend_cloudfront_distribution_id)"
set_github_variable "FRONTEND_CLOUDFRONT_URL" "$(terraform_dev_output frontend_cloudfront_url)"
set_github_variable "VITE_API_BASE_URL" "$(terraform_dev_output api_stage_invoke_url)"
set_github_variable "VITE_COGNITO_HOSTED_UI_BASE_URL" "$(terraform_dev_output cognito_hosted_ui_base_url)"
set_github_variable "VITE_COGNITO_CLIENT_ID" "$(terraform_dev_output cognito_user_pool_client_id)"

info "GitHub Environment variables updated. Values were not printed."
