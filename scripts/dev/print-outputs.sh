#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
terraform_dev_init

print_named_output "API_URL" "api_stage_invoke_url"
print_named_output "COGNITO_HOSTED_UI" "cognito_hosted_ui_base_url"
print_named_output "COGNITO_CLIENT_ID" "cognito_user_pool_client_id"
print_named_output "USER_POOL_ID" "cognito_user_pool_id"
print_named_output "FRONTEND_BUCKET" "frontend_bucket_name"
print_named_output "FRONTEND_DISTRIBUTION_ID" "frontend_cloudfront_distribution_id"
print_named_output "FRONTEND_URL" "frontend_cloudfront_url"
