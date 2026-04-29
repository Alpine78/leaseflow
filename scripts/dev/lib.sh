#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
BOOTSTRAP_TF_DIR="${REPO_ROOT}/infra/bootstrap/terraform_state"
DEV_TF_DIR="${REPO_ROOT}/infra/environments/dev"
FRONTEND_DIR="${REPO_ROOT}/frontend"
LAMBDA_ARTIFACT="${REPO_ROOT}/dist/leaseflow-backend.zip"

export AWS_PROFILE="${AWS_PROFILE:-terraform}"
export AWS_REGION="${AWS_REGION:-eu-north-1}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION}}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

require_linux() {
  [[ "$(uname -s)" == "Linux" ]] || die "Run this script in WSL/Linux."
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

require_file() {
  [[ -f "$1" ]] || die "Missing required file: $1"
}

require_dir() {
  [[ -d "$1" ]] || die "Missing required directory: $1"
}

require_repo_root() {
  require_dir "${REPO_ROOT}/infra"
  require_dir "${REPO_ROOT}/backend"
  require_file "${FRONTEND_DIR}/package.json"
}

require_dev_backend_config() {
  require_file "${DEV_TF_DIR}/backend.hcl"
}

require_dev_tfvars() {
  require_file "${DEV_TF_DIR}/terraform.tfvars"
}

reject_placeholder_dev_tfvars() {
  if grep -q "replace-with-a-unique-dev-prefix" "${DEV_TF_DIR}/terraform.tfvars"; then
    die "Replace cognito_hosted_ui_domain_prefix in infra/environments/dev/terraform.tfvars first."
  fi
}

terraform_dev_init() {
  require_command terraform
  require_dev_backend_config
  terraform -chdir="${DEV_TF_DIR}" init -backend-config=backend.hcl -input=false >/dev/null
}

terraform_dev_output() {
  local output_name="$1"
  terraform -chdir="${DEV_TF_DIR}" output -raw "${output_name}"
}

print_named_output() {
  local name="$1"
  local output_name="$2"
  printf '%s=%s\n' "${name}" "$(terraform_dev_output "${output_name}")"
}
