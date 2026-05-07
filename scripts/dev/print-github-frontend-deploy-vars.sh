#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
terraform_dev_init

printf 'AWS_REGION=%s\n' "${AWS_REGION}"
print_named_output "FRONTEND_DEPLOY_ROLE_ARN" "frontend_deploy_role_arn"
print_named_output "FRONTEND_BUCKET_NAME" "frontend_bucket_name"
print_named_output "FRONTEND_CLOUDFRONT_DISTRIBUTION_ID" "frontend_cloudfront_distribution_id"
print_named_output "FRONTEND_CLOUDFRONT_URL" "frontend_cloudfront_url"
print_named_output "VITE_API_BASE_URL" "api_stage_invoke_url"
print_named_output "VITE_COGNITO_HOSTED_UI_BASE_URL" "cognito_hosted_ui_base_url"
print_named_output "VITE_COGNITO_CLIENT_ID" "cognito_user_pool_client_id"
