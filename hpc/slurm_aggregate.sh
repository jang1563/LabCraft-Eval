#!/usr/bin/env bash
#SBATCH --job-name=bpb-aggregate
#SBATCH --output=results/hpc/slurm/%x_%j.out
#SBATCH --error=results/hpc/slurm/%x_%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-${SLURM_SUBMIT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}}"
cd "$REPO_ROOT"

: "${RUN_ID:?Set RUN_ID to the bundle name under results/hpc.}"
: "${TASK_PRESET:=auto}"
: "${MODELS:=}"
: "${VENV_DIR:=/home/fs01/jak4013/labcraft-py313}"
: "${BUNDLE_DIR:=${REPO_ROOT}/results/hpc/${RUN_ID}}"
: "${LOG_DIR:=${BUNDLE_DIR}/logs}"
: "${RESULTS_OUT:=${BUNDLE_DIR}/results.md}"
: "${PLOTS_OUT_DIR:=${BUNDLE_DIR}/plots}"

mkdir -p "$BUNDLE_DIR" "$PLOTS_OUT_DIR" "${REPO_ROOT}/results/hpc/slurm"

python_exec() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    "${PYTHON_BIN}" "$@"
    return
  fi
  if [ -x "${VENV_DIR}/bin/python" ]; then
    "${VENV_DIR}/bin/python" "$@"
    return
  fi
  if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    "${REPO_ROOT}/.venv/bin/python" "$@"
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
    return
  fi
  python3 "$@"
}

COMMIT_SHA="$(git rev-parse HEAD)"
MANIFEST_COUNT=$(find "${BUNDLE_DIR}/manifests" -name 'cell_*.json' -type f 2>/dev/null | wc -l | tr -d ' ')
EVAL_COUNT=$(find "${LOG_DIR}" -name '*.eval' -type f 2>/dev/null | wc -l | tr -d ' ')

cat > "${BUNDLE_DIR}/aggregate_manifest.json" <<EOF
{
  "schema_version": "1.0.0",
  "run_id": "${RUN_ID}",
  "commit_sha": "${COMMIT_SHA}",
  "task_preset": "${TASK_PRESET}",
  "models": "${MODELS}",
  "log_dir": "${LOG_DIR}",
  "results_out": "${RESULTS_OUT}",
  "plots_out_dir": "${PLOTS_OUT_DIR}",
  "manifest_count": ${MANIFEST_COUNT},
  "eval_count": ${EVAL_COUNT}
}
EOF

echo "Aggregating LabCraft-Eval HPC bundle"
echo "  run_id:         ${RUN_ID}"
echo "  commit_sha:     ${COMMIT_SHA}"
echo "  log_dir:        ${LOG_DIR}"
echo "  eval_count:     ${EVAL_COUNT}"
echo "  results_out:    ${RESULTS_OUT}"
echo "  plots_out_dir:  ${PLOTS_OUT_DIR}"
echo

python_exec scripts/aggregate_eval_results.py \
  --log-dir "${LOG_DIR}" \
  --out "${RESULTS_OUT}"

if [ "$TASK_PRESET" = "safety_case" ]; then
  echo
  echo "Skipping scorecard plots for safety_case; safety axes are reported in ${RESULTS_OUT}."
  echo "Bundle aggregation complete: ${BUNDLE_DIR}"
  exit 0
fi

plot_args=(
  scripts/plot_scorecard.py
  --log-dir "${LOG_DIR}"
  --out-dir "${PLOTS_OUT_DIR}"
  --task-preset "${TASK_PRESET}"
)

if [ -n "$MODELS" ]; then
  read -r -a MODEL_ARRAY <<< "$MODELS"
  plot_args+=(--models "${MODEL_ARRAY[@]}")
fi

python_exec "${plot_args[@]}"

echo
echo "Bundle aggregation complete: ${BUNDLE_DIR}"
