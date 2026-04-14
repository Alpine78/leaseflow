#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "Build must run in WSL/Linux so Lambda dependencies are Linux-compatible." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/dist/lambda-build"
VENV_DIR="${REPO_ROOT}/dist/lambda-venv"
ARTIFACT="${REPO_ROOT}/dist/leaseflow-backend.zip"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
NORMALIZED_TIMESTAMP="${NORMALIZED_TIMESTAMP:-202601010000.00}"

for command_name in "${PYTHON_BIN}" rsync zip; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

cd "${REPO_ROOT}"

rm -rf "${BUILD_DIR}" "${VENV_DIR}" "${ARTIFACT}"
mkdir -p "${BUILD_DIR}"

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
python -m pip install --no-cache-dir ./backend -t "${BUILD_DIR}"
deactivate

cp backend/alembic.ini "${BUILD_DIR}/alembic.ini"
rsync -a --delete backend/migrations/ "${BUILD_DIR}/migrations/"

find "${BUILD_DIR}" -type d \
  \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ruff_cache" -o -name "tests" \) \
  -prune -exec rm -rf {} +
find "${BUILD_DIR}" -type f \
  \( -name "*.pyc" -o -name "*.pyo" -o -name ".DS_Store" -o -name "direct_url.json" \) \
  -delete

# Normalize mtimes and zip entry ordering to keep review diffs stable enough for dev deploys.
find "${BUILD_DIR}" -exec touch -h -t "${NORMALIZED_TIMESTAMP}" {} +
(
  cd "${BUILD_DIR}"
  find . -type f -print | LC_ALL=C sort | zip -X -q "${ARTIFACT}" -@
)

rm -rf "${VENV_DIR}"

echo "Built ${ARTIFACT}"
