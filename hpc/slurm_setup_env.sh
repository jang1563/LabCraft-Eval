#!/usr/bin/env bash
#SBATCH --job-name=bpb-setup
#SBATCH --output=results/hpc/slurm/%x_%j.out
#SBATCH --error=results/hpc/slurm/%x_%j.err
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$REPO_ROOT"

: "${VENV_DIR:=/home/fs01/jak4013/labcraft-py313}"
: "${PYTHON_MODULE:=python/3.13.7}"

if [ -n "${PYTHON_MODULE}" ]; then
  if ! command -v module >/dev/null 2>&1 && [ -f /etc/profile.d/lmod.sh ]; then
    # Batch shells do not always initialize Lmod.
    # shellcheck disable=SC1091
    source /etc/profile.d/lmod.sh
  fi
  module load "${PYTHON_MODULE}"
fi

: "${PYTHON_BIN:=$(command -v python3)}"

mkdir -p "${REPO_ROOT}/results/hpc/slurm"

echo "Preparing LabCraft-Eval HPC Python environment"
echo "  repo:     ${REPO_ROOT}"
echo "  venv:     ${VENV_DIR}"
echo "  module:   ${PYTHON_MODULE}"
echo "  python:   ${PYTHON_BIN}"
echo

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -e ".[dev,analysis]"
"${VENV_DIR}/bin/python" -m pip install openai anthropic

echo
"${VENV_DIR}/bin/python" --version
"${VENV_DIR}/bin/inspect" --version
echo "Environment ready."
