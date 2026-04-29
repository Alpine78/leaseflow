#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command terraform
require_dev_backend_config
require_dev_tfvars
require_file "${LAMBDA_ARTIFACT}"
reject_placeholder_dev_tfvars

info "Initializing dev Terraform with remote state"
terraform -chdir="${DEV_TF_DIR}" init -backend-config=backend.hcl

info "Validating dev Terraform"
terraform -chdir="${DEV_TF_DIR}" validate

info "Applying dev Terraform interactively"
terraform -chdir="${DEV_TF_DIR}" apply
