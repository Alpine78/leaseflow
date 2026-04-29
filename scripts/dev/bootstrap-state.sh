#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root
require_command terraform

info "Bootstrapping Terraform remote state with AWS_PROFILE=${AWS_PROFILE} AWS_REGION=${AWS_REGION}"
terraform -chdir="${BOOTSTRAP_TF_DIR}" init
terraform -chdir="${BOOTSTRAP_TF_DIR}" apply

info "Writing dev backend config"
terraform -chdir="${BOOTSTRAP_TF_DIR}" output -raw dev_backend_config > "${DEV_TF_DIR}/backend.hcl"

info "Wrote infra/environments/dev/backend.hcl"
