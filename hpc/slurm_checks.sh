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
echo "Running ruff"
"${VENV_DIR}/bin/python" -m ruff check .

echo
echo "Running pytest"
"${VENV_DIR}/bin/python" -m pytest -q

echo
echo "HPC checks complete."
