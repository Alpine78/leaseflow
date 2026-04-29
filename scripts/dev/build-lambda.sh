#!/usr/bin/env bash
set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/lib.sh"

require_linux
require_repo_root

export PYTHON_BIN="${PYTHON_BIN:-${LAMBDA_PYTHON:-python3.12}}"

info "Building Lambda artifact with PYTHON_BIN=${PYTHON_BIN}"
bash "${REPO_ROOT}/scripts/build_lambda_artifact.sh"
