#!/usr/bin/env bash
#SBATCH --job-name=bpb-checks
#SBATCH --output=results/hpc/slurm/%x_%j.out
#SBATCH --error=results/hpc/slurm/%x_%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}}"
: "${VENV_DIR:=/home/fs01/jak4013/labcraft-py313}"
: "${CHECK_ROOT:=${TMPDIR:-/tmp}/bioprotocolbench_checks_${SLURM_JOB_ID:-manual}}"

mkdir -p "${REPO_ROOT}/results/hpc/slurm"
if [ -e "${CHECK_ROOT}" ]; then
  echo "Check root already exists: ${CHECK_ROOT}" >&2
  echo "Set CHECK_ROOT to a fresh directory." >&2
  exit 1
fi
mkdir -p "${CHECK_ROOT}"

echo "Preparing isolated check copy"
echo "  repo:       ${REPO_ROOT}"
echo "  check_root: ${CHECK_ROOT}"
echo "  python:     ${VENV_DIR}/bin/python"
echo

# Preserve .git so provenance-sensitive tests exercise the real commit and
# repository identity inside the isolated copy.
rsync -a \
  --exclude '.venv/' \
  --exclude '.uv-cache/' \
  --exclude '.uv-cache-discovery/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '.matplotlib/' \
  --exclude 'build/' \
  --exclude 'dist/' \
  --exclude '*.egg-info/' \
  --exclude 'results/hpc/' \
  "${REPO_ROOT}/" "${CHECK_ROOT}/"

cd "${CHECK_ROOT}"

echo "Checking Slurm shell script syntax"
bash -n hpc/*.sh

echo
echo "Validating central model registry"
"${VENV_DIR}/bin/python" scripts/model_matrix.py validate

echo
echo "Running ruff"
"${VENV_DIR}/bin/python" -m ruff check .

echo
echo "Running pytest"
# Tests that spawn the HPC runner must resolve provenance against this isolated
# copy, not the submit checkout inherited through the outer job environment.
REPO_ROOT="${CHECK_ROOT}" "${VENV_DIR}/bin/python" -m pytest -q

echo
echo "Building and smoke-testing the wheel outside the source checkout"
PACKAGE_SMOKE_ROOT="${CHECK_ROOT}/package_smoke"
mkdir -p "${PACKAGE_SMOKE_ROOT}/wheels" "${PACKAGE_SMOKE_ROOT}/run"
"${VENV_DIR}/bin/python" -m pip wheel \
  --no-deps \
  --wheel-dir "${PACKAGE_SMOKE_ROOT}/wheels" \
  .
WHEEL_PATH=$(find "${PACKAGE_SMOKE_ROOT}/wheels" -name 'labcraft-*.whl' -print -quit)
if [ -z "$WHEEL_PATH" ]; then
  echo "Could not find the built labcraft wheel." >&2
  exit 1
fi
"${VENV_DIR}/bin/python" -m venv "${PACKAGE_SMOKE_ROOT}/venv"
"${PACKAGE_SMOKE_ROOT}/venv/bin/python" -m pip install "$WHEEL_PATH"
(
  cd "${PACKAGE_SMOKE_ROOT}/run"
  "${PACKAGE_SMOKE_ROOT}/venv/bin/python" "${CHECK_ROOT}/scripts/package_smoke.py"
)

echo
echo "HPC checks complete."
